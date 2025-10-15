import json
import random
import re


class PoolAgent:
    def __init__(self, pool_id: int, pledge: float, margin: float, cost: float, client, model: str, base_temperature: float, persona: str):
        self.pool_id = pool_id
        self.pledge = pledge
        self.margin = margin
        self.cost = cost
        self.client = client
        self.model = model
        self.persona = persona
        self.temperature = self._adjust_temperature(base_temperature)
        min_interval, max_interval, skip_probability = self._get_activity_profile()
        self._min_update_interval = max(1, min_interval)
        self._max_update_interval = max(self._min_update_interval, max_interval)
        self._skip_probability = max(0.0, min(1.0, skip_probability))
        self.next_update_round = 0
        self.stake_delegated = 0.0
        self.reward = 0.0
        self.gross_reward = 0.0
        self.profit_history = []

    def _get_activity_profile(self):
        """
        Returns (min_interval, max_interval, skip_probability) tuned by pool persona.
        """
        profiles = {
            # Profit-focused operators react quickly to market signals.
            "Profit Maximizer": (1, 2, 0.05),
            # Community pools adjust occasionally to stay aligned with supporters.
            "Community Builder": (3, 6, 0.2),
            # Corporate operations prize stability; they rarely change knobs.
            "Corporate Pool": (6, 12, 0.45),
        }
        return profiles.get(self.persona, (4, 8, 0.25))

    def _get_persona_prompt(self) -> str:
        prompts = {
            "Community Builder": "You are a mission-driven community builder. You focus on providing value through content or tools and maintain fair, stable fees to build long-term trust. You avoid aggressive, profit-maximizing behavior.",
            "Profit Maximizer": "Your goal is to maximize profit. You will aggressively adjust your margin and costs based on market dynamics. You might lower fees to attract stake when you are new, and raise them as you become established.",
            "Corporate Pool": "You represent a large, professional staking operation. You prioritize reliability, security, and stability. You maintain a very high pledge and stable, competitive fees to attract institutional and risk-averse delegators. You do not engage in aggressive fee wars."
        }
        return prompts.get(self.persona, "You are a standard pool operator.")

    def _adjust_temperature(self, base_temperature: float) -> float:
        """Pool personas tend to be more conservative; adjust the sampling noise."""
        offsets = {
            "Community Builder": -0.1,
            "Profit Maximizer": 0.1,
            "Corporate Pool": -0.15,
        }
        adjusted = base_temperature + offsets.get(self.persona, 0.0)
        return max(0.0, min(1.5, adjusted))

    def _schedule_next_update(self, current_round: int):
        span = random.randint(self._min_update_interval, self._max_update_interval)
        self.next_update_round = current_round + span

    def _parse_parameters_response(self, content: str) -> dict:
        if not content:
            return {}

        candidates = []
        params_match = re.search(r"PARAMETERS_JSON:\s*(\{.*\})", content, re.DOTALL)
        if params_match:
            candidates.append(params_match.group(1))

        json_like = re.findall(r"\{[\s\S]*?\}", content)
        for candidate in json_like:
            if candidate not in candidates:
                candidates.append(candidate)

        for candidate in candidates:
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data

        return {}

    def compute_reward(self, total_rewards, s_opt, a0):
        # This formula calculates the pool's total reward for an epoch.
        # It is based on the pool's stake, pledge, and the network's parameters.
        s = self.stake_delegated + self.pledge
        
        # The saturation factor ensures rewards don't grow linearly with stake indefinitely.
        saturation_factor = min(s / s_opt, 1.0) if s > 0 else 0.0
        
        # The pledge influence factor (a0) gives a bonus to pools with higher pledge.
        incentive_factor = (1 - a0 * (self.pledge / s if s > 0 else 0))
        gross_reward = max((total_rewards * saturation_factor) * incentive_factor, 0.0)
        self.gross_reward = gross_reward
        self.reward = max(self.gross_reward - self.cost, 0.0)
        return self.reward

    def compute_user_reward(self, user_stake):
        s = self.stake_delegated + self.pledge
        if s <= 0 or self.reward <= 0:
            return 0.0
        # Users get a proportional share of the pool's reward after the margin is taken.
        delegator_share = self.reward * (1 - self.margin)
        return (user_stake / s) * delegator_share

    def update_parameters(self, current_round: int):
        if current_round < self.next_update_round:
            return  # Not time for another update yet.

        if self.profit_history and random.random() < self._skip_probability:
            # The operator is content with the current strategy and skips.
            self._schedule_next_update(current_round)
            return

        prompt = (
            f"You are the operator of pool {self.pool_id}.\n"
            f"Your persona is: {self.persona}. {self._get_persona_prompt()}\n\n"
            f"Current parameters: pledge={self.pledge:.1f}, margin={self.margin:.3f}, cost={self.cost:.1f}\n"
            f"Total delegated stake: {self.stake_delegated:.1f}\n"
            f"Current pool reward: {self.reward:.1f}\n"
            "Think about how to adjust pledge, margin, and cost to improve long-term profitability while staying aligned with your persona.\n"
            "Follow these steps:\n"
            "1. Under the heading 'Thought', reason about the adjustments you will make.\n"
            "2. Output a single line starting with 'PARAMETERS_JSON:' followed by a JSON object of the form "
            "{\"pledge\": <float>, \"margin\": <float between 0 and 1>, \"cost\": <float>}.\n"
            "3. The values must be numeric (not strings) and realistic given the current state."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You simulate a Cardano stake pool operator. Analyze carefully and obey formatting instructions."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content if response.choices else ""
        except Exception as exc:
            print(f"[PoolAgent {self.pool_id}] LLM call failed: {exc}")
            self._schedule_next_update(current_round)
            return

        params = self._parse_parameters_response(content)
        if not params:
            self._schedule_next_update(current_round)
            return

        pledge = params.get("pledge", self.pledge)
        margin = params.get("margin", self.margin)
        cost = params.get("cost", self.cost)

        try:
            pledge = float(pledge)
        except (TypeError, ValueError):
            pledge = self.pledge
        try:
            margin = float(margin)
        except (TypeError, ValueError):
            margin = self.margin
        try:
            cost = float(cost)
        except (TypeError, ValueError):
            cost = self.cost

        self.pledge = max(0.0, pledge)
        self.margin = min(max(0.0, margin), 1.0)
        self.cost = max(0.0, cost)
        self._schedule_next_update(current_round)
