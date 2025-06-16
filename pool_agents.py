import json
from langchain.schema import HumanMessage
from pydantic import BaseModel, Field
class PoolAgent:
    def __init__(self, pool_id: int, pledge: float, margin: float, cost: float, llm):
        self.pool_id = pool_id
        self.pledge = pledge
        self.margin = margin
        self.cost = cost
        self.llm = llm

        self.stake_delegated = 0.0
        self.reward = 0.0
        self.profit_history = []

    def compute_reward(self, total_rewards, s_opt, a0):
        s = self.stake_delegated + self.pledge
        saturation_factor = min(s / s_opt, 1.0) if s > 0 else 0.0
        self.reward = max(
            (total_rewards * saturation_factor) * (1 - a0 * (self.pledge / s if s > 0 else 0)) - self.cost,
            0.0,
        )
        return self.reward

    def compute_user_reward(self, user_stake):
        s = self.stake_delegated + self.pledge
        if s == 0 or self.reward == 0:
            return 0.0
        return user_stake * self.reward * (1 - self.margin) / s

    def update_parameters(self):
        prompt = (
            f"You are the operator of pool {self.pool_id}.\n"
            f"Current parameters: pledge={self.pledge:.1f}, margin={self.margin:.2f}, cost={self.cost:.1f}\n"
            f"Total delegated stake: {self.stake_delegated:.1f}\n"
            f"Current pool reward: {self.reward:.1f}\n"
            "Suggest new parameters to improve profitability.\n"

        )
        structured_llm = self.llm.with_structured_output(PoolAgentReturn)
        resp = structured_llm.invoke([HumanMessage(content=prompt)])
        pledge, margin, cost = resp.pledge, resp.margin, resp.cost
        self.pledge = max(0, pledge)
        self.margin = min(max(0, margin), 1)
        self.cost = max(0, cost)

class PoolAgentReturn(BaseModel):
    pledge: float = Field(..., description="The new pledge amount")
    margin: float = Field(..., description="The new margin amount(between 0 and 1)")
    cost: float = Field(..., description="The new cost amount")
