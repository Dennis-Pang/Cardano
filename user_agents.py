import json
import random
import re
from typing import List
from pydantic import BaseModel, Field
from prompts import build_user_decision_prompt, build_user_system_prompt, get_user_persona_prompt

class UserMultiPoolReturn(BaseModel):
    pool_id: int = Field(..., description="The pool id to delegate to")
    stake_amount: float = Field(..., description="The stake amount to delegate")


class UserAgent:
    def __init__(self, user_id: int, stake: float, llm, persona: str, history_window: int = 5):
        self.user_id = user_id
        self.stake = stake
        self.llm = llm
        self.persona = persona
        self.stake_allocation: List[UserMultiPoolReturn] = []
        self.reward_history: List[float] = []
        self.update_frequency = self._get_update_frequency()
        self.allocation_history: List[List[dict]] = []
        self.last_decision_json = "[]"
        self.last_response_text = ""
        self.last_thought = ""
        self.history_window = history_window
        self.migration_chance = random.uniform(0.01, 0.05)

    def _get_update_frequency(self) -> int:
        frequencies = {
            "Decentralization Maximalist": 4,
            "Mission-Driven Delegator": 10,
            "Passive Yield-Seeker": 12,
            "Active Yield-Farmer": 1,
            "Brand Loyalist": 8,
            "Risk-Averse Institutional": 6,
        }
        return frequencies.get(self.persona, 5) # Default to 5

    def choose_pools(
        self,
        pool_state_summary: str,
        user_delegation_summary: str,
        saturation_size: float,
        current_round: int
    ):
        should_rebalance = (
            current_round == 0
            or (
                current_round % self.update_frequency == 0
                and random.random() < self.migration_chance
            )
        )
        if not should_rebalance and self.stake_allocation:
            self._store_allocation(current_round, self.stake_allocation)
            return # Skip updating strategy this round

        persona_prompt = get_user_persona_prompt(self.persona)
        migration_hint = f"{self.migration_chance*100:.1f}% of this cohort typically shifts per round"
        system_prompt = build_user_system_prompt(
            self.persona,
            persona_prompt,
            self.history_window,
            migration_hint,
        )
        recent_history = self._build_recent_history()
        prompt = build_user_decision_prompt(
            stake=self.stake,
            round_number=current_round + 1,
            saturation_size=saturation_size,
            pool_state_summary=pool_state_summary,
            user_delegation_summary=user_delegation_summary,
            recent_history=recent_history,
        )

        response = self.llm.chat(prompt, system_prompt=system_prompt)
        self.last_response_text = response
        self.last_thought = self._extract_thought(response)
        allocations = self._extract_allocations(response)

        if not allocations and self.stake_allocation:
            # Fallback to previous allocation if parsing failed
            allocations = [
                UserMultiPoolReturn(pool_id=alloc.pool_id, stake_amount=alloc.stake_amount)
                for alloc in self.stake_allocation
            ]

        self.stake_allocation = allocations
        self._store_allocation(current_round, allocations)

    def _build_recent_history(self) -> str:
        if not self.reward_history:
            return "No completed rounds yet."
        lines = []
        for idx, (allocs, reward) in enumerate(zip(self.allocation_history, self.reward_history), start=1):
            alloc_str = ", ".join(
                f"POOL{entry['pool_id']}::{entry['stake_amount']:.1f}"
                for entry in allocs
            )
            lines.append(f"Round {idx}: reward={reward:.2f}, allocations={alloc_str}")
        return "\n".join(lines[-self.history_window:])

    def _extract_allocations(self, text: str) -> List[UserMultiPoolReturn]:
        pattern = re.compile(r"POOL\s*(\d+)\s*::\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
        allocations_map = {}
        for pool_id_str, amount_str in pattern.findall(text):
            pool_id = int(pool_id_str)
            amount = float(amount_str)
            allocations_map[pool_id] = allocations_map.get(pool_id, 0.0) + amount

        allocations = [
            UserMultiPoolReturn(pool_id=pool_id, stake_amount=amount)
            for pool_id, amount in allocations_map.items()
        ]
        return allocations

    def _store_allocation(self, current_round: int, allocations: List[UserMultiPoolReturn]) -> None:
        alloc_dicts = [
            {"pool_id": alloc.pool_id, "stake_amount": alloc.stake_amount}
            for alloc in allocations
        ]
        if current_round < len(self.allocation_history):
            self.allocation_history[current_round] = alloc_dicts
        else:
            self.allocation_history.append(alloc_dicts)
        self.last_decision_json = json.dumps(alloc_dicts)

    def _extract_thought(self, text: str) -> str:
        match = re.search(
            r"THOUGHT\s*:\s*(.*?)\n\s*SELECTIONS",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return match.group(1).strip() if match else ""
