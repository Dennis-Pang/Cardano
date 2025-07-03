import json
import random
from langchain.schema import HumanMessage
from pydantic import BaseModel, Field

class PoolAgentReturn(BaseModel):
    pledge: float = Field(..., description="The new pledge amount")
    margin: float = Field(..., description="The new margin amount (between 0 and 1)")
    cost: float = Field(..., description="The new cost amount")

class PoolAgent:
    def __init__(self, pool_id: int, pledge: float, margin: float, cost: float, llm, persona: str):
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

    def _get_update_frequency(self) -> int:
        frequencies = {
            "Community Builder": 5,
            "Profit Maximizer": 2,
            "Corporate Pool": 8,
        }
        return frequencies.get(self.persona, 4)

    def _get_persona_prompt(self) -> str:
        prompts = {
            "Community Builder": "You are a mission-driven community builder. You focus on providing value through content or tools and maintain fair, stable fees to build long-term trust. You avoid aggressive, profit-maximizing behavior.",
            "Profit Maximizer": "Your goal is to maximize profit. You will aggressively adjust your margin and costs based on market dynamics. You might lower fees to attract stake when you are new, and raise them as you become established.",
            "Corporate Pool": "You represent a large, professional staking operation. You prioritize reliability, security, and stability. You maintain a very high pledge and stable, competitive fees to attract institutional and risk-averse delegators. You do not engage in aggressive fee wars."
        }
        return prompts.get(self.persona, "You are a standard pool operator.")

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
            return # Skip updating strategy this round

        prompt = (
            f"You are the operator of pool {self.pool_id}.\n"
            f"Your persona is: {self.persona}. {self._get_persona_prompt()}\n\n"
            f"Current parameters: pledge={self.pledge:.1f}, margin={self.margin:.2f}, cost={self.cost:.1f}\n"
            f"Total delegated stake: {self.stake_delegated:.1f}\n"
            f"Current pool reward: {self.reward:.1f}\n"
            "Suggest new parameters to improve profitability, keeping your persona in mind.\n"
        )
        structured_llm = self.llm.with_structured_output(PoolAgentReturn)
        resp = structured_llm.invoke([HumanMessage(content=prompt)])
        pledge, margin, cost = resp.pledge, resp.margin, resp.cost
        self.pledge = max(0, pledge)
        self.margin = min(max(0, margin), 1)
        self.cost = max(0, cost)

