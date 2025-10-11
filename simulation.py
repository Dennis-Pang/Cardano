import json
import os
import random
import time
from typing import Dict, List, Tuple

import numpy as np
from dotenv import load_dotenv

from constants import A0, S_OPT, TOTAL_REWARDS
from ollama_client import OllamaLLM
from pool_agents import PoolAgent
from user_agents import UserAgent


# Load environment variables
# Explicitly load the .env file from the script's directory to ensure it's found.
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=dotenv_path)

USER_HISTORY_WINDOW = int(os.environ.get("CARDANO_USER_HISTORY_WINDOW", "5"))
POOL_HISTORY_WINDOW = int(os.environ.get("CARDANO_POOL_HISTORY_WINDOW", "5"))
POOL_ADJUSTMENT_CAP = float(os.environ.get("CARDANO_POOL_ADJUSTMENT_CAP", "0.05"))
REWARD_NOISE_STD = float(os.environ.get("CARDANO_REWARD_NOISE_STD", "0.01"))
SHOCK_INTERVAL = int(os.environ.get("CARDANO_SHOCK_INTERVAL", "50"))
SHOCK_COST_DELTA = float(os.environ.get("CARDANO_SHOCK_COST_DELTA", "0.002"))
HEAD_SHARE_RANGE: Tuple[float, float] = (
    float(os.environ.get("CARDANO_HEAD_SHARE_MIN", "0.45")),
    float(os.environ.get("CARDANO_HEAD_SHARE_MAX", "0.60")),
)


def seed_pool_delegations(pools: List[PoolAgent], total_funds: float) -> None:
    if not pools:
        return
    head_count = max(1, len(pools) // 10)
    head_share = random.uniform(*HEAD_SHARE_RANGE)
    tail_share = max(0.0, 1.0 - head_share)

    sorted_pools = sorted(pools, key=lambda p: p.pledge, reverse=True)
    head = sorted_pools[:head_count]
    tail = sorted_pools[head_count:]

    head_weights = np.random.dirichlet(np.ones(len(head))) if head else np.array([])
    tail_weights = np.random.dirichlet(np.ones(len(tail))) if tail else np.array([])

    for idx, pool in enumerate(head):
        base = head_share * total_funds * head_weights[idx]
        pool.base_delegation = base
        pool.stake_delegated = base

    for idx, pool in enumerate(tail):
        base = tail_share * total_funds * (tail_weights[idx] if len(tail_weights) else 0.0)
        pool.base_delegation = base
        pool.stake_delegated = base

    for pool in pools:
        if not hasattr(pool, "base_delegation"):
            pool.base_delegation = 0.0
            pool.stake_delegated = 0.0


def apply_structural_shock(pools: List[PoolAgent], round_idx: int, reward_multiplier: float) -> Tuple[float, str]:
    if SHOCK_INTERVAL <= 0 or (round_idx + 1) % SHOCK_INTERVAL != 0:
        return reward_multiplier, ""

    for pool in pools:
        pool.cost *= 1 + SHOCK_COST_DELTA
        pool.margin = min(pool.margin + SHOCK_COST_DELTA, 0.15)
    new_multiplier = reward_multiplier * (1 - SHOCK_COST_DELTA)
    message = (
        f"Structural shock: network congestion increases costs by {SHOCK_COST_DELTA*100:.2f}% "
        f"and trims rewards. Reward multiplier now {new_multiplier:.3f}"
    )
    return new_multiplier, message

# ====== Summary Builders ======
def build_pool_state_summary(pools: List[PoolAgent]) -> str:
    return "\n".join(
        f"Pool {p.pool_id}: pledge={p.pledge:.1f}, margin={p.margin:.2f}, "
        f"cost={p.cost:.1f}, total_stake={p.stake_delegated + p.pledge:.1f}, "
        f"reward_prev_round={p.reward:.1f}"
        for p in sorted(pools, key=lambda p: p.pool_id)
    )

def build_user_delegation_summary(users: List[UserAgent], pools: List[PoolAgent]) -> str:
    lines = []
    for user in users:
        stake_map = {a.pool_id: a.stake_amount for a in user.stake_allocation}
        line = ", ".join(
            f"Pool {p.pool_id}: {stake_map.get(p.pool_id, 0):.0f}"
            for p in sorted(pools, key=lambda p: p.pool_id)
        )
        lines.append(f"User {user.user_id}: {line}")
    return "\n".join(lines)

# ====== Stake Generator ======
def generate_powerlaw_stakes(
    num_users: int,
    total_funds: float,
    alpha: float = 2.0,
    min_stake: float = 500,
    max_stake: float = None,
    seed: int = 42
) -> List[float]:
    np.random.seed(seed)
    samples = np.random.pareto(alpha, num_users) + 1
    stakes = samples / samples.sum()
    stakes = stakes * total_funds
    if max_stake is not None:
        stakes = np.clip(stakes, min_stake, max_stake)
    else:
        stakes = np.maximum(stakes, min_stake)
    stakes = stakes / stakes.sum() * total_funds
    return stakes.tolist()

def process_user_choices(
    users: List[UserAgent],
    pool_state_summary: str,
    user_delegation_summary: str,
    saturation_size: float,
    round_idx: int,
):
    total_users = len(users)
    log_interval = max(1, total_users // 10) if total_users else 1
    round_label = round_idx + 1
    for idx, user in enumerate(users):
        user.choose_pools(
            pool_state_summary,
            user_delegation_summary,
            saturation_size,
            round_idx
        )
        if (idx + 1) % log_interval == 0 or (idx + 1) == total_users:
            print(
                f"[Round {round_label}] Delegator decisions {idx + 1}/{total_users}",
                flush=True
            )

# ====== Simulation Runner ======
def run_simulation_sync(num_rounds=100, num_users=30, num_pools=80):
    model_name = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct")
    llm = OllamaLLM(model=model_name, temperature=0.0)

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    output_dir = os.path.join("results", timestamp)
    os.makedirs(output_dir, exist_ok=True)

    log_filepath = os.path.join(output_dir, "simulation_log.txt")
    json_filepath = os.path.join(output_dir, "simulation_results.json")

    saturation_size = S_OPT
    total_funds = saturation_size * num_pools
    stakes = generate_powerlaw_stakes(num_users=num_users, total_funds=total_funds)

    # Define user personas and their distribution weights
    user_persona_distribution = {
        "Decentralization Maximalist": 0.20,
        "Mission-Driven Delegator": 0.15,
        "Passive Yield-Seeker": 0.35,
        "Active Yield-Farmer": 0.05,
        "Brand Loyalist": 0.15,
        "Risk-Averse Institutional": 0.10,
    }
    user_personas = random.choices(
        list(user_persona_distribution.keys()),
        weights=list(user_persona_distribution.values()),
        k=num_users
    )
    users: List[UserAgent] = [
        UserAgent(
            user_id=i + 1,
            stake=stake,
            llm=llm,
            persona=user_personas[i],
            history_window=USER_HISTORY_WINDOW,
        )
        for i, stake in enumerate(stakes)
    ]

    # Define pool personas and their distribution
    pool_persona_distribution = {
        "Community Builder": 0.4,
        "Profit Maximizer": 0.3,
        "Corporate Pool": 0.3,
    }
    pool_personas = random.choices(
        list(pool_persona_distribution.keys()),
        weights=list(pool_persona_distribution.values()),
        k=num_pools
    )
    pools: List[PoolAgent] = [
        PoolAgent(
            pool_id=i + 1,
            pledge=random.uniform(100_000, 1_000_000),
            margin=random.uniform(0.01, 0.05),
            cost=random.uniform(500, 2000),
            llm=llm,
            persona=pool_personas[i],
            history_window=POOL_HISTORY_WINDOW,
            adjustment_cap=POOL_ADJUSTMENT_CAP,
        )
        for i in range(num_pools)
    ]
    seed_pool_delegations(pools, total_funds)

    history = []
    reward_multiplier = 1.0

    with open(log_filepath, "w", encoding="utf-8") as log_file:
        for round_idx in range(num_rounds):
            print(f"Running simulation round {round_idx + 1} / {num_rounds}")
            round_log = []
            if round_idx > 0:
                round_log.append("")
            round_log.append(f"=== Simulation Round {round_idx + 1} ===")
            reward_multiplier, shock_message = apply_structural_shock(pools, round_idx, reward_multiplier)
            if shock_message:
                round_log.append(shock_message)

            pool_state_summary = build_pool_state_summary(pools)
            user_delegation_summary = build_user_delegation_summary(users, pools)

            process_user_choices(
                users,
                pool_state_summary,
                user_delegation_summary,
                saturation_size,
                round_idx
            )

            pool_delegations: Dict[int, List[float]] = {p.pool_id: [] for p in pools}
            for user in users:
                for alloc in user.stake_allocation:
                    pool_delegations[alloc.pool_id].append(alloc.stake_amount)

            for pool in pools:
                user_total = sum(pool_delegations[pool.pool_id])
                pool.stake_delegated = getattr(pool, "base_delegation", 0.0) + user_total
                pool.compute_reward(TOTAL_REWARDS * reward_multiplier, S_OPT, A0)
                noise = random.gauss(0, REWARD_NOISE_STD)
                pool.reward = max(pool.reward * (1 + noise), 0.0)

            pool_map = {p.pool_id: p for p in pools}
            for user in users:
                reward = sum(
                    pool_map[alloc.pool_id].compute_user_reward(alloc.stake_amount)
                    for alloc in user.stake_allocation
                )
                user.reward_history.append(reward)

            total_pools = len(pools)
            pool_log_interval = max(1, total_pools // 5) if total_pools else 1
            for idx, pool in enumerate(pools):
                pool.update_parameters(round_idx)
                profit = (
                    pool.reward * pool.margin
                    + (pool.reward - pool.cost) * (1 - pool.margin)
                    - pool.cost
                )
                pool.profit_history.append(profit)
                if (idx + 1) % pool_log_interval == 0 or (idx + 1) == total_pools:
                    print(
                        f"[Round {round_idx + 1}] Pool updates {idx + 1}/{total_pools}",
                        flush=True
                    )

            round_log.append("Pool States:")
            for pool in pools:
                round_log.append(
                    f"Pool {pool.pool_id}: pledge={pool.pledge:.1f}, margin={pool.margin:.3f}, cost={pool.cost:.1f}, "
                    f"stake_delegated={pool.stake_delegated:.1f}, reward={pool.reward:.1f}, profit={pool.profit_history[-1]:.1f}"
                )

            round_log.append("\nUser Delegations and Rewards:")
            for user in users:
                stake_map = {a.pool_id: a.stake_amount for a in user.stake_allocation}
                deleg_str = ", ".join(
                    f"Pool {pool.pool_id}: {stake_map.get(pool.pool_id, 0):.0f}"
                    for pool in sorted(pools, key=lambda p: p.pool_id)
                )
                round_log.append(f"User {user.user_id}: {deleg_str}, reward {user.reward_history[-1]:.1f}")

            round_record = {
                "round": round_idx + 1,
                "pools": [
                    {
                        "pool_id": p.pool_id,
                        "pledge": p.pledge,
                        "margin": p.margin,
                        "cost": p.cost,
                        "stake_delegated": p.stake_delegated,
                        "reward": p.reward,
                        "profit": p.profit_history[-1],
                    }
                    for p in pools
                ],
                "users": [
                    {
                        "user_id": u.user_id,
                        "stake": u.stake,
                        "allocations": [
                            {"pool_id": a.pool_id, "stake_amount": a.stake_amount}
                            for a in u.stake_allocation
                        ],
                        "reward": u.reward_history[-1],
                    }
                    for u in users
                ]
            }
            history.append(round_record)

            log_file.write("\n".join(round_log) + "\n")
            log_file.flush()
            with open(json_filepath, "w", encoding="utf-8") as f_json:
                json.dump(history, f_json, indent=2)
        
    print(f"Simulation completed successfully. Results saved in {output_dir}")
    return history

def run_simulation(num_rounds=100, num_users=30, num_pools=80):
    return run_simulation_sync(num_rounds, num_users, num_pools)
