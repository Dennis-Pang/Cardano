import json
import re
from prompts import build_pool_decision_prompt, build_pool_system_prompt, get_pool_persona_prompt


class PoolAgent:
    def __init__(
        self,
        pool_id: int,
        pledge: float,
        margin: float,
        cost: float,
        llm,
        persona: str,
        history_window: int = 5,
        adjustment_cap: float = 0.05,
    ):
        self.pool_id = pool_id
        self.pledge = pledge
        self.margin = margin
        self.cost = cost
        self.llm = llm
        self.persona = persona
        self.stake_delegated = 0.0
        self.reward = 0.0
        self.profit_history = []
        self.update_frequency = self._get_update_frequency()
        self.parameter_history = []
        self.last_param_json = json.dumps(
            {"pledge": self.pledge, "margin": self.margin, "cost": self.cost}
        )
        self.last_response_text = ""
        self.last_thought = ""
        self.history_window = history_window
        self.adjustment_cap = adjustment_cap

    def _get_update_frequency(self) -> int:
        frequencies = {
            "Community Builder": 5,
            "Profit Maximizer": 2,
            "Corporate Pool": 8,
        }
        return frequencies.get(self.persona, 4)

    def compute_reward(self, total_rewards, s_opt, a0):
        # This formula calculates the pool's total reward for an epoch.
        # It is based on the pool's stake, pledge, and the network's parameters.
        s = self.stake_delegated + self.pledge
        
        # The saturation factor ensures rewards don't grow linearly with stake indefinitely.
        saturation_factor = min(s / s_opt, 1.0) if s > 0 else 0.0
        
        # The pledge influence factor (a0) gives a bonus to pools with higher pledge.
        self.reward = max(
            (total_rewards * saturation_factor) * (1 - a0 * (self.pledge / s if s > 0 else 0)) - self.cost,
            0.0,
        )
        return self.reward

    def compute_user_reward(self, user_stake):
        s = self.stake_delegated + self.pledge
        if s == 0 or self.reward == 0:
            return 0.0
        # Users get a proportional share of the pool's reward after the margin is taken.
        return user_stake * self.reward * (1 - self.margin) / s

    def update_parameters(self, current_round: int):
        if current_round % self.update_frequency != 0:
            self._store_parameters(current_round, self.pledge, self.margin, self.cost)
            return # Skip updating strategy this round

        persona_prompt = get_pool_persona_prompt(self.persona)
        system_prompt = build_pool_system_prompt(
            self.persona,
            persona_prompt,
            self.adjustment_cap,
            self.history_window,
            "1-2%",
        )
        recent_history = self._build_recent_history()
        prompt = build_pool_decision_prompt(
            pool_id=self.pool_id,
            pledge=self.pledge,
            margin=self.margin,
            cost=self.cost,
            stake_delegated=self.stake_delegated,
            reward=self.reward,
            recent_history=recent_history,
        )
        response = self.llm.chat(prompt, system_prompt=system_prompt)
        self.last_response_text = response
        self.last_thought = self._extract_thought(response)
        params = self._extract_parameters(response)

        if params is None:
            params = (self.pledge, self.margin, self.cost)

        pledge, margin, cost = params
        self.pledge = max(0.0, self._limit_step(self.pledge, pledge))
        self.margin = min(max(0.0, self._limit_step(self.margin, margin)), 1.0)
        self.cost = max(0.0, self._limit_step(self.cost, cost))
        self._store_parameters(current_round, self.pledge, self.margin, self.cost)

    def _build_recent_history(self) -> str:
        if not self.profit_history or not self.parameter_history:
            return "No completed rounds yet."
        lines = []
        for idx, (params, profit) in enumerate(
            zip(self.parameter_history, self.profit_history), start=1
        ):
            lines.append(
                f"Round {idx}: pledge={params['pledge']:.1f}, margin={params['margin']:.3f}, "
                f"cost={params['cost']:.1f}, profit={profit:.2f}"
            )
        return "\n".join(lines[-self.history_window:])

    def _extract_parameters(self, text: str):
        pledge_match = re.search(r"PLEDGE\s*::\s*([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        margin_match = re.search(r"MARGIN\s*::\s*([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        cost_match = re.search(r"COST\s*::\s*([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)

        if not (pledge_match and margin_match and cost_match):
            return None

        return (
            float(pledge_match.group(1)),
            float(margin_match.group(1)),
            float(cost_match.group(1)),
        )

    def _extract_thought(self, text: str) -> str:
        match = re.search(
            r"THOUGHT\s*:\s*(.*?)\n\s*PARAMS",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return match.group(1).strip() if match else ""

    def _store_parameters(self, current_round: int, pledge: float, margin: float, cost: float) -> None:
        params_dict = {"pledge": pledge, "margin": margin, "cost": cost}
        if current_round < len(self.parameter_history):
            self.parameter_history[current_round] = params_dict
        else:
            self.parameter_history.append(params_dict)
        self.last_param_json = json.dumps(params_dict)

    def _limit_step(self, previous: float, proposed: float) -> float:
        if previous <= 0:
            return proposed
        max_delta = previous * self.adjustment_cap
        delta = max(min(proposed - previous, max_delta), -max_delta)
        return previous + delta
