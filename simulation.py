import random
from typing import List, Dict
from langchain_openai import ChatOpenAI
from user_agents import UserAgent
from pool_agents import PoolAgent
from constants import TOTAL_REWARDS, S_OPT, A0
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Set API key explicitly
os.environ["OPENAI_API_KEY"] = "api-key"

def run_simulation(num_rounds=10, num_users=100, num_pools=10):
    llm = ChatOpenAI(model_name="gpt-4o-2024-08-06", temperature=0)

    pools: List[PoolAgent] = [
        PoolAgent(
            pool_id=i + 1,
            pledge=random.uniform(100000, 1000000),
            margin=random.uniform(0.01, 0.05),
            cost=random.uniform(500, 2000),
            llm=llm,
        )
        for i in range(num_pools)
    ]

    users: List[UserAgent] = [
        UserAgent(user_id=i + 1, stake=1000, llm=llm)
        for i in range(num_users)
    ]

    history = []

    for round_idx in range(num_rounds):
        print(f"\n=== Simulation Round {round_idx + 1} ===")

        # Step 1: Users choose pools
        for user in users:
            user.choose_pool(pools)

        # Step 2: Aggregate delegations for each pool
        pool_delegations: Dict[int, List[float]] = {p.pool_id: [] for p in pools}
        for user in users:
            pool_delegations[user.delegated_pool].append(user.stake)

        # Step 3: Update pool delegations and calculate rewards
        for pool in pools:
            delegated_stakes = pool_delegations[pool.pool_id]
            pool.stake_delegated = sum(delegated_stakes)
            pool.compute_reward(TOTAL_REWARDS, S_OPT, A0)

        # Step 4: Calculate actual user rewards
        for user in users:
            pool = next(p for p in pools if p.pool_id == user.delegated_pool)
            r = pool.compute_user_reward(user.stake)
            user.reward_history.append(r)

        # Step 5: Pool operators update parameters
        for pool in pools:
            pool.update_parameters()
            profit = (
                pool.reward * pool.margin
                + (pool.reward - pool.cost) * (1 - pool.margin)
                - pool.cost
            )
            pool.profit_history.append(profit)

        # Step 6: Record round data
        print("Pool States:")
        for pool in pools:
            print(
                f"Pool {pool.pool_id}: pledge={pool.pledge:.1f}, margin={pool.margin:.3f}, cost={pool.cost:.1f}, "
                f"stake_delegated={pool.stake_delegated:.1f}, reward={pool.reward:.1f}, profit={pool.profit_history[-1]:.1f}"
            )

        print("\nUser Delegations and Rewards:")
        for user in users:
            print(f"User {user.user_id}: delegated pool {user.delegated_pool}, reward {user.reward_history[-1]:.1f}")

        history.append(
            {
                "round": round_idx + 1,
                "pools": [
                    (
                        p.pool_id,
                        p.pledge,
                        p.margin,
                        p.cost,
                        p.stake_delegated,
                        p.reward,
                        p.profit_history[-1],
                    )
                    for p in pools
                ],
                "users_sample": [
                    (users[0].user_id, users[0].delegated_pool, users[0].reward_history[-1])
                ],
            }
        )

    return history
