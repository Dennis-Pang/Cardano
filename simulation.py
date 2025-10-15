import json
import os
import random
import time
from typing import List, Dict
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from user_agents import UserAgent
from pool_agents import PoolAgent
from constants import TOTAL_REWARDS, S_OPT, A0


# Load environment variables
# Explicitly load the .env file from the script's directory to ensure it's found.
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=dotenv_path)

# ====== LLM Factory ======
def build_chat_model():
    """Create an OpenAI-compatible client targeting the local Ollama server."""
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    api_key = os.environ.get("OLLAMA_API_KEY", "ollama")
    model_name = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct")
    temperature = float(os.environ.get("LLM_TEMPERATURE", "0.0"))
    client = OpenAI(base_url=base_url, api_key=api_key)
    return client, model_name, temperature

# ====== Summary Builders ======
def build_pool_state_summary(pools: List[PoolAgent]) -> str:
    return "\n".join(
        f"Pool {p.pool_id}: pledge={p.pledge:.1f}, margin={p.margin:.2f}, "
        f"cost={p.cost:.1f}, total_stake={p.stake_delegated + p.pledge:.1f}"
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

def build_reward_summary(pools: List[PoolAgent]) -> str:
    if not pools:
        return ""
    return "\n".join(
        f"Pool {p.pool_id}: reward_previous_round={p.reward:.1f}"
        for p in sorted(pools, key=lambda p: p.pool_id)
    )

def build_round_briefing(
    round_idx: int,
    pools: List[PoolAgent],
    users: List[UserAgent],
    saturation_size: float
) -> str:
    pool_summary = build_pool_state_summary(pools)
    user_summary = build_user_delegation_summary(users, pools)
    reward_summary = build_reward_summary(pools)

    if not pool_summary:
        pool_summary = "No pools configured."
    if not user_summary:
        user_summary = "No delegations yet."
    if not reward_summary:
        reward_summary = "No rewards have been distributed yet."

    return (
        f"Round {round_idx + 1} network briefing\n"
        f"Saturation size (network defined): {saturation_size:.1f} ADA.\n\n"
        f"--- Pool Parameters (current round) ---\n{pool_summary}\n\n"
        f"--- Delegations per User (current round) ---\n{user_summary}\n\n"
        f"--- Pool Rewards (previous round) ---\n{reward_summary}"
    )

def compute_gini(values: List[float]) -> float:
    """Compute the Gini coefficient for a list of non-negative values."""
    filtered = [v for v in values if v >= 0]
    count = len(filtered)
    if count == 0:
        return 0.0
    filtered.sort()
    mean = sum(filtered) / count
    if mean == 0:
        return 0.0
    gini_sum = 0.0
    for idx, value in enumerate(filtered, start=1):
        gini_sum += value * (2 * idx - count - 1)
    return gini_sum / (count * count * mean)

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
    u = np.random.uniform(0, 1, num_users)
    stakes = min_stake * (1 - u) ** (-1 / (alpha - 1))
    if max_stake is not None:
        stakes = np.clip(stakes, min_stake, max_stake)
    stakes = stakes / stakes.sum() * total_funds
    return stakes.tolist()

def process_user_choices(
    users: List[UserAgent],
    round_briefing: str,
    saturation_size: float,
    round_idx: int,
):
    """同步处理用户选择"""
    for user in users:
        user.choose_pools(
            round_briefing,
            saturation_size,
            round_idx
        )

# ====== Simulation Runner ======
def run_simulation_sync(num_rounds=10, num_users=100, num_pools=10):
    llm_client, llm_model, llm_temperature = build_chat_model()

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
            client=llm_client,
            model=llm_model,
            base_temperature=llm_temperature,
            persona=user_personas[i]
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
            client=llm_client,
            model=llm_model,
            base_temperature=llm_temperature,
            persona=pool_personas[i]
        )
        for i in range(num_pools)
    ]

    history = []
    log_lines = []

    # ====== Prepare output directory (write incrementally) ======
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    output_dir = os.path.join("results", timestamp)
    os.makedirs(output_dir, exist_ok=True)
    log_filepath = os.path.join(output_dir, "simulation_log.txt")
    json_filepath = os.path.join(output_dir, "simulation_results.json")

    def flush_outputs():
        with open(log_filepath, "w", encoding="utf-8") as f_txt:
            f_txt.write("\n".join(log_lines))
        with open(json_filepath, "w", encoding="utf-8") as f_json:
            json.dump(history, f_json, indent=2)

    for round_idx in range(num_rounds):
        print(f"Running simulation round {round_idx + 1} / {num_rounds}")
        log_lines.append(f"\n=== Simulation Round {round_idx + 1} ===")
        round_briefing = build_round_briefing(
            round_idx=round_idx,
            pools=pools,
            users=users,
            saturation_size=saturation_size
        )
        log_lines.append("Round briefing shared with users:")
        log_lines.append(round_briefing)

        # 并发处理用户选择
        process_user_choices(
            users,
            round_briefing,
            saturation_size,
            round_idx
        )

        print("User delegation decisions:")
        total_users = len(users)
        sorted_pools = sorted(pools, key=lambda p: p.pool_id)
        for idx, user in enumerate(users, start=1):
            stake_map = {a.pool_id: a.stake_amount for a in user.stake_allocation}
            allocations_str = ", ".join(
                f"Pool {pool.pool_id}: {stake_map.get(pool.pool_id, 0):.1f}"
                for pool in sorted_pools
            )
            print(f"[{idx}/{total_users}] User {user.user_id}: {allocations_str}")
            log_lines.append(f"[{idx}/{total_users}] User {user.user_id}: {allocations_str}")

        pool_delegations: Dict[int, List[float]] = {p.pool_id: [] for p in pools}
        for user in users:
            for alloc in user.stake_allocation:
                pool_delegations[alloc.pool_id].append(alloc.stake_amount)

        for pool in pools:
            pool.stake_delegated = sum(pool_delegations[pool.pool_id])
            pool.compute_reward(TOTAL_REWARDS, S_OPT, A0)

        pool_map = {p.pool_id: p for p in pools}
        for user in users:
            reward = sum(
                pool_map[alloc.pool_id].compute_user_reward(alloc.stake_amount)
                for alloc in user.stake_allocation
            )
            user.reward_history.append(reward)

        user_wealths = [
            user.stake + sum(user.reward_history)
            for user in users
        ]
        pool_total_stakes = [
            pool.stake_delegated + pool.pledge
            for pool in pools
        ]
        user_gini = compute_gini(user_wealths)
        pool_gini = compute_gini(pool_total_stakes)
        print(f"Gini (user wealth): {user_gini:.4f} | Gini (pool total stake): {pool_gini:.4f}")

        for pool in pools:
            pool.update_parameters(round_idx)
            total_stake = pool.stake_delegated + pool.pledge
            delegator_share = pool.reward * (1 - pool.margin)
            operator_margin_reward = pool.reward * pool.margin
            operator_pledge_share = 0.0
            if total_stake > 0 and delegator_share > 0:
                operator_pledge_share = (pool.pledge / total_stake) * delegator_share
            profit = operator_margin_reward + operator_pledge_share
            pool.profit_history.append(profit)

        log_lines.append("Pool States:")
        for pool in pools:
            log_lines.append(
                f"Pool {pool.pool_id}: pledge={pool.pledge:.1f}, margin={pool.margin:.3f}, cost={pool.cost:.1f}, "
                f"stake_delegated={pool.stake_delegated:.1f}, gross_reward={pool.gross_reward:.1f}, net_reward={pool.reward:.1f}, profit={pool.profit_history[-1]:.1f}"
            )

        log_lines.append(f"Gini (user wealth): {user_gini:.4f}")
        log_lines.append(f"Gini (pool total stake): {pool_gini:.4f}")

        log_lines.append("\nUser Delegations and Rewards:")
        for user in users:
            stake_map = {a.pool_id: a.stake_amount for a in user.stake_allocation}
            deleg_str = ", ".join(
                f"Pool {pool.pool_id}: {stake_map.get(pool.pool_id, 0):.0f}"
                for pool in sorted(pools, key=lambda p: p.pool_id)
            )
            log_lines.append(f"User {user.user_id}: {deleg_str}, reward {user.reward_history[-1]:.1f}")

        history.append(
            {
                "round": round_idx + 1,
                "briefing": round_briefing,
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
                ],
                "metrics": {
                    "gini_user_wealth": user_gini,
                    "gini_pool_total_stake": pool_gini,
                }
            }
        )
        flush_outputs()

    print(f"Simulation completed successfully. Results saved in {output_dir}")
    return history

def run_simulation(num_rounds=10, num_users=100, num_pools=10):
    """同步版本的包装器，调用同步版本"""
    return run_simulation_sync(num_rounds, num_users, num_pools)
