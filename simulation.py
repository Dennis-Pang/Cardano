import json
import os
import random
import time
from typing import List, Dict
import numpy as np
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from user_agents import UserAgent
from pool_agents import PoolAgent
from constants import TOTAL_REWARDS, S_OPT, A0


# Load environment variables
# Explicitly load the .env file from the script's directory to ensure it's found.
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path=dotenv_path)

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
    u = np.random.uniform(0, 1, num_users)
    stakes = min_stake * (1 - u) ** (-1 / (alpha - 1))
    if max_stake is not None:
        stakes = np.clip(stakes, min_stake, max_stake)
    stakes = stakes / stakes.sum() * total_funds
    return stakes.tolist()

def process_user_choices(
    users: List[UserAgent],
    pool_state_summary: str,
    user_delegation_summary: str,
    saturation_size: float,
    round_idx: int,
):
    """同步处理用户选择"""
    for user in users:
        user.choose_pools(
            pool_state_summary,
            user_delegation_summary,
            saturation_size,
            round_idx
        )

# ====== Simulation Runner ======
def run_simulation_sync(num_rounds=10, num_users=100, num_pools=10):
    llm = ChatGroq(model="llama3-8b-8192", temperature=0.0)

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
        UserAgent(user_id=i + 1, stake=stake, llm=llm, persona=user_personas[i])
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
            persona=pool_personas[i]
        )
        for i in range(num_pools)
    ]

    history = []
    log_lines = []

    for round_idx in range(num_rounds):
        print(f"Running simulation round {round_idx + 1} / {num_rounds}")
        log_lines.append(f"\n=== Simulation Round {round_idx + 1} ===")
        pool_state_summary = build_pool_state_summary(pools)
        user_delegation_summary = build_user_delegation_summary(users, pools)

        # 并发处理用户选择
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
            pool.stake_delegated = sum(pool_delegations[pool.pool_id])
            pool.compute_reward(TOTAL_REWARDS, S_OPT, A0)

        pool_map = {p.pool_id: p for p in pools}
        for user in users:
            reward = sum(
                pool_map[alloc.pool_id].compute_user_reward(alloc.stake_amount)
                for alloc in user.stake_allocation
            )
            user.reward_history.append(reward)

        for pool in pools:
            pool.update_parameters(round_idx)
            profit = (
                pool.reward * pool.margin
                + (pool.reward - pool.cost) * (1 - pool.margin)
                - pool.cost
            )
            pool.profit_history.append(profit)

        log_lines.append("Pool States:")
        for pool in pools:
            log_lines.append(
                f"Pool {pool.pool_id}: pledge={pool.pledge:.1f}, margin={pool.margin:.3f}, cost={pool.cost:.1f}, "
                f"stake_delegated={pool.stake_delegated:.1f}, reward={pool.reward:.1f}, profit={pool.profit_history[-1]:.1f}"
            )

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
        )

    # ====== Write results to file ======
    # Create a unique timestamped directory for this simulation run
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    output_dir = os.path.join("results", timestamp)
    os.makedirs(output_dir, exist_ok=True)

    # Define file paths
    log_filepath = os.path.join(output_dir, "simulation_log.txt")
    json_filepath = os.path.join(output_dir, "simulation_results.json")

    # Write text log
    with open(log_filepath, "w", encoding="utf-8") as f_txt:
        f_txt.write("\n".join(log_lines))

    # Write structured data as JSON
    with open(json_filepath, "w", encoding="utf-8") as f_json:
        json.dump(history, f_json, indent=2)
        
    print(f"Simulation completed successfully. Results saved in {output_dir}")
    return history

def run_simulation(num_rounds=10, num_users=100, num_pools=10):
    """同步版本的包装器，调用同步版本"""
    return run_simulation_sync(num_rounds, num_users, num_pools)