from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Stakeholder:
    stakeholder_id: int
    total_stake: float
    operates_pool: bool = False
    pool_id: Optional[int] = None
    pledge: float = 0.0
    delegated_pool_id: Optional[int] = None
    last_reward: float = 0.0
    reward_history: List[float] = field(default_factory=list)

    def available_delegation(self) -> float:
        if self.operates_pool:
            return max(self.total_stake - self.pledge, 0.0)
        return self.total_stake

    def assign_delegation(self, pool_id: int) -> None:
        self.delegated_pool_id = pool_id

    def record_reward(self, value: float) -> None:
        self.last_reward = value
        self.reward_history.append(value)


@dataclass
class Pool:
    pool_id: int
    operator: Stakeholder
    margin: float
    cost: float
    adjustment_cap: float = 0.05
    delegators: Dict[int, float] = field(default_factory=dict)  # stakeholder_id -> stake
    total_stake: float = 0.0
    reward: float = 0.0
    delegator_reward: float = 0.0
    operator_reward: float = 0.0
    delegator_roi: float = 0.0
    operator_roi: float = 0.0
    history: List[Dict[str, float]] = field(default_factory=list)

    def reset_round_state(self) -> None:
        self.total_stake = 0.0
        self.reward = 0.0
        self.delegator_reward = 0.0
        self.operator_reward = 0.0
        self.delegator_roi = 0.0
        self.operator_roi = 0.0
        self.delegators.clear()

    def add_delegation(self, stakeholder: Stakeholder, amount: float) -> None:
        if amount <= 0:
            return
        self.delegators[stakeholder.stakeholder_id] = self.delegators.get(stakeholder.stakeholder_id, 0.0) + amount

    def append_history_entry(self) -> None:
        self.history.append(
            {
                "total_stake": self.total_stake,
                "reward": self.reward,
                "delegator_roi": self.delegator_roi,
                "operator_roi": self.operator_roi,
                "margin": self.margin,
                "cost": self.cost,
            }
        )

    def clamp_parameters(self, proposed_margin: float, proposed_cost: float) -> None:
        self.margin = self._clamp_change(self.margin, proposed_margin, 0.0, 1.0)
        self.cost = self._clamp_change(self.cost, proposed_cost, 0.0, None)

    def _clamp_change(self, current: float, proposed: float, lower: float, upper: Optional[float]) -> float:
        if current == 0:
            value = max(proposed, lower)
            if upper is not None:
                value = min(value, upper)
            return value
        delta_limit = current * self.adjustment_cap
        value = current + max(min(proposed - current, delta_limit), -delta_limit)
        if upper is not None:
            value = min(value, upper)
        return max(value, lower)
