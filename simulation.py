import json
import os
import random
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv

from constants import A0, S_OPT, TOTAL_REWARDS
from stakeholders import Pool, Stakeholder


dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=dotenv_path)

USER_HISTORY_WINDOW = int(os.environ.get("CARDANO_USER_HISTORY_WINDOW", "5"))
POOL_HISTORY_WINDOW = int(os.environ.get("CARDANO_POOL_HISTORY_WINDOW", "5"))
POOL_ADJUSTMENT_CAP = float(os.environ.get("CARDANO_POOL_ADJUSTMENT_CAP", "0.05"))
REWARD_NOISE_STD = float(os.environ.get("CARDANO_REWARD_NOISE_STD", "0.01"))
MIGRATION_RATE = float(os.environ.get("CARDANO_MIGRATION_RATE", "0.05"))
IMPROVEMENT_THRESHOLD = float(os.environ.get("CARDANO_IMPROVEMENT_THRESHOLD", "0.02"))
SHOCK_INTERVAL = int(os.environ.get("CARDANO_SHOCK_INTERVAL", "50"))
SHOCK_COST_DELTA = float(os.environ.get("CARDANO_SHOCK_COST_DELTA", "0.002"))
HEAD_SHARE_RANGE: Tuple[float, float] = (
    float(os.environ.get("CARDANO_HEAD_SHARE_MIN", "0.45")),
    float(os.environ.get("CARDANO_HEAD_SHARE_MAX", "0.60")),
)


def generate_powerlaw_stakes(
    count: int,
    total_funds: float,
    alpha: float = 2.0,
    min_stake: float = 1_000.0,
    seed: int = 42,
) -> List[float]:
    np.random.seed(seed)
    samples = np.random.pareto(alpha, count) + 1
    stakes = samples / samples.sum()
    stakes = stakes * total_funds
    stakes = np.maximum(stakes, min_stake)
    stakes = stakes / stakes.sum() * total_funds
    return stakes.tolist()


def create_stakeholders_and_pools(
    num_stakeholders: int,
    num_pools: int,
    total_funds: float,
) -> Tuple[List[Stakeholder], Dict[int, Pool]]:
    if num_stakeholders < num_pools:
        raise ValueError("Number of stakeholders must be at least the number of pools.")

    stakes = generate_powerlaw_stakes(num_stakeholders, total_funds)
    stakeholders = [Stakeholder(i + 1, stake) for i, stake in enumerate(stakes)]

    pools: Dict[int, Pool] = {}
    for idx in range(num_pools):
        stakeholder = stakeholders[idx]
        stakeholder.operates_pool = True
        stakeholder.pool_id = idx + 1
        pledge_fraction = random.uniform(0.1, 0.4)
        stakeholder.pledge = min(stakeholder.total_stake, stakeholder.total_stake * pledge_fraction)
        stakeholder.assign_delegation(stakeholder.pool_id)
        pools[stakeholder.pool_id] = Pool(
            pool_id=stakeholder.pool_id,
            operator=stakeholder,
            margin=random.uniform(0.02, 0.05),
            cost=random.uniform(600, 1_500),
            adjustment_cap=POOL_ADJUSTMENT_CAP,
        )

    delegators = stakeholders[num_pools:]
    assign_initial_delegations(delegators, pools)
    return stakeholders, pools


def assign_initial_delegations(delegators: List[Stakeholder], pools: Dict[int, Pool]) -> None:
    if not delegators or not pools:
        return
    pool_ids = sorted(pools.keys())
    head_count = max(1, len(pool_ids) // 10)
    head_ids = pool_ids[:head_count]
    tail_ids = pool_ids[head_count:] or pool_ids
    head_share = random.uniform(*HEAD_SHARE_RANGE)

    for delegator in delegators:
        choose_head = random.random() < head_share or not tail_ids
        candidate_ids = head_ids if choose_head else tail_ids
        delegator.assign_delegation(random.choice(candidate_ids))


def rss_reward(total_rewards: float, sigma: float, pledge_ratio: float, z0: float, a0: float) -> float:
    if sigma <= 0.0:
        return 0.0
    sigma_prime = min(sigma, z0)
    pledge_prime = min(pledge_ratio, sigma_prime)
    reward_factor = total_rewards / (1 + a0)
    bonus = 0.0
    if z0 > 0 and sigma_prime > 0:
        bonus = pledge_prime * a0 * (sigma_prime - pledge_prime * (z0 - sigma_prime) / z0)
    return max(reward_factor * (sigma_prime + max(bonus, 0.0)), 0.0)


def apply_structural_shock(pools: Dict[int, Pool], round_idx: int) -> Optional[str]:
    if SHOCK_INTERVAL <= 0 or (round_idx + 1) % SHOCK_INTERVAL != 0:
        return None
    for pool in pools.values():
        pool.cost *= 1 + SHOCK_COST_DELTA
        pool.margin = min(pool.margin + SHOCK_COST_DELTA, 0.15)
    return (
        f"Structural shock: network congestion increased costs and nudged fees upward by {SHOCK_COST_DELTA*100:.2f}%."
    )


def compute_concentration_metrics(pools: Dict[int, Pool], total_stake: float) -> Tuple[float, int]:
    if total_stake <= 0:
        return 0.0, 0
    shares = sorted((pool.total_stake / total_stake for pool in pools.values()), reverse=True)
    hhi = sum((share * 100) ** 2 for share in shares)
    cumulative = 0.0
    nakamoto = 0
    for share in shares:
        cumulative += share
        nakamoto += 1
        if cumulative >= 0.5:
            break
    return hhi, nakamoto


def run_simulation_sync(num_rounds: int = 100, num_users: int = 300, num_pools: int = 100):
    saturation_size = S_OPT
    total_funds = saturation_size * num_pools

    stakeholders, pools = create_stakeholders_and_pools(num_users, num_pools, total_funds)
    stakeholder_lookup = {s.stakeholder_id: s for s in stakeholders}

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    output_dir = os.path.join("results", timestamp)
    os.makedirs(output_dir, exist_ok=True)
    log_path = os.path.join(output_dir, "simulation_log.txt")
    json_path = os.path.join(output_dir, "simulation_results.json")

    history: List[Dict] = []
    with open(log_path, "w", encoding="utf-8") as log_file:
        for round_idx in range(num_rounds):
            print(f"Running simulation round {round_idx + 1} / {num_rounds}")
            round_lines: List[str] = []
            if round_idx:
                round_lines.append("")
            round_lines.append(f"=== Simulation Round {round_idx + 1} ===")
            shock_msg = apply_structural_shock(pools, round_idx)
            if shock_msg:
                round_lines.append(shock_msg)

            for pool in pools.values():
                pool.reset_round_state()
                pool.total_stake += pool.operator.pledge
                operator_extra = pool.operator.available_delegation()
                if operator_extra > 0:
                    pool.add_delegation(pool.operator, operator_extra)
                    pool.total_stake += operator_extra

            for stakeholder in stakeholders:
                if stakeholder.operates_pool or stakeholder.delegated_pool_id is None:
                    continue
                amount = stakeholder.available_delegation()
                if amount <= 0:
                    continue
                pool = pools[stakeholder.delegated_pool_id]
                pool.add_delegation(stakeholder, amount)
                pool.total_stake += amount

            total_network_stake = sum(pool.total_stake for pool in pools.values())
            z0 = 1.0 / num_pools if num_pools > 0 else 0.0

            for pool in pools.values():
                sigma = pool.total_stake / total_network_stake if total_network_stake > 0 else 0.0
                pledge_ratio = pool.operator.pledge / total_network_stake if total_network_stake > 0 else 0.0
                reward = rss_reward(TOTAL_REWARDS, sigma, pledge_ratio, z0, A0)
                noise = random.gauss(0, REWARD_NOISE_STD)
                pool.reward = max(reward * (1 + noise), 0.0)

                if pool.reward <= pool.cost:
                    pool.operator_reward = pool.reward
                    pool.delegator_reward = 0.0
                    pool.delegator_roi = 0.0
                    pool.operator_roi = pool.operator_reward / pool.operator.total_stake
                    pool.append_history_entry()
                    continue

                after_cost = pool.reward - pool.cost
                margin_cut = after_cost * pool.margin
                remainder = after_cost - margin_cut

                delegator_stake = max(pool.total_stake - pool.operator.pledge, 0.0)
                if delegator_stake > 0 and pool.total_stake > 0:
                    pool.delegator_reward = remainder * (delegator_stake / pool.total_stake)
                else:
                    pool.delegator_reward = 0.0

                variable_for_operator = remainder - pool.delegator_reward
                pool.operator_reward = pool.cost + margin_cut + max(variable_for_operator, 0.0)

                pool.delegator_roi = (
                    pool.delegator_reward / delegator_stake if delegator_stake > 0 else 0.0
                )
                pool.operator_roi = (
                    pool.operator_reward / pool.operator.total_stake if pool.operator.total_stake > 0 else 0.0
                )
                pool.append_history_entry()

            for pool in pools.values():
                delegator_total = sum(pool.delegators.values())
                for stakeholder_id, amount in pool.delegators.items():
                    payout = pool.delegator_reward * amount / delegator_total if delegator_total > 0 else 0.0
                    stakeholder = stakeholder_lookup[stakeholder_id]
                    if stakeholder.operates_pool and stakeholder.pool_id == pool.pool_id:
                        payout += pool.operator_reward
                    stakeholder.record_reward(payout)

            for stakeholder in stakeholders:
                if len(stakeholder.reward_history) < round_idx + 1:
                    stakeholder.record_reward(0.0)

            delegators = [s for s in stakeholders if not s.operates_pool and s.delegated_pool_id is not None]
            migrations = max(1, int(len(delegators) * MIGRATION_RATE)) if delegators else 0
            movers = random.sample(delegators, migrations) if migrations else []

            for stakeholder in movers:
                current_pool_id = stakeholder.delegated_pool_id
                current_roi = pools[current_pool_id].delegator_roi
                best_pool_id = current_pool_id
                best_roi = current_roi
                for pool_id, pool in pools.items():
                    if pool.delegator_roi > best_roi * (1 + IMPROVEMENT_THRESHOLD):
                        best_pool_id = pool_id
                        best_roi = pool.delegator_roi
                if best_pool_id != current_pool_id and best_roi > current_roi * (1 + IMPROVEMENT_THRESHOLD):
                    stakeholder.assign_delegation(best_pool_id)

            round_lines.append("Pools:")
            for pool in sorted(pools.values(), key=lambda p: p.pool_id):
                round_lines.append(
                    f"Pool {pool.pool_id}: stake={pool.total_stake:,.0f}, reward={pool.reward:,.0f}, "
                    f"delegator_roi={pool.delegator_roi:.4f}, margin={pool.margin:.3f}, cost={pool.cost:,.0f}"
                )

            round_lines.append("\nSample stakeholders:")
            for stakeholder in stakeholders[:10]:
                round_lines.append(
                    f"Stakeholder {stakeholder.stakeholder_id}: pool={stakeholder.delegated_pool_id}, "
                    f"last_reward={stakeholder.last_reward:,.2f}"
                )

            hhi, nakamoto = compute_concentration_metrics(pools, total_network_stake)

            history.append(
                {
                    "round": round_idx + 1,
                    "metrics": {"hhi": hhi, "nakamoto": nakamoto},
                    "pools": [
                        {
                            "pool_id": pool.pool_id,
                            "operator_id": pool.operator.stakeholder_id,
                            "total_stake": pool.total_stake,
                            "pledge": pool.operator.pledge,
                            "margin": pool.margin,
                            "cost": pool.cost,
                            "reward": pool.reward,
                            "delegator_roi": pool.delegator_roi,
                            "operator_roi": pool.operator_roi,
                        }
                        for pool in sorted(pools.values(), key=lambda p: p.pool_id)
                    ],
                    "stakeholders": [
                        {
                            "stakeholder_id": stakeholder.stakeholder_id,
                            "operates_pool": stakeholder.operates_pool,
                            "pool_id": stakeholder.pool_id,
                            "delegated_pool": stakeholder.delegated_pool_id,
                            "total_stake": stakeholder.total_stake,
                            "pledge": stakeholder.pledge,
                            "last_reward": stakeholder.last_reward,
                        }
                        for stakeholder in stakeholders
                    ],
                }
            )

            log_file.write("\n".join(round_lines) + "\n")
            log_file.flush()
            with open(json_path, "w", encoding="utf-8") as json_file:
                json.dump(history, json_file, indent=2)

    print(f"Simulation completed successfully. Results saved in {output_dir}")
    return history


def run_simulation(num_rounds: int = 100, num_users: int = 300, num_pools: int = 100):
    return run_simulation_sync(num_rounds, num_users, num_pools)
