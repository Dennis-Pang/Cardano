import json
from langchain.schema import HumanMessage
from typing import List
from pool_agents import PoolAgent
from pydantic import BaseModel, Field

class UserMultiPoolReturn(BaseModel):
    pool_id: int = Field(..., description="The pool id to delegate to")
    stake_amount: float = Field(..., description="The stake amount to delegate")

class UserMultiPoolReturnList(BaseModel):
    allocations: List[UserMultiPoolReturn]

class UserAgent:
    def __init__(self, user_id: int, stake: float, llm):
        self.user_id = user_id
        self.stake = stake
        self.llm = llm
        self.stake_allocation: List[UserMultiPoolReturn] = []
        self.reward_history = []

    def choose_pools(
        self,
        pool_state_summary: str,
        user_delegation_summary: str,
        saturation_size: float
    ):
        prompt = (
            f"You are a Cardano user with {self.stake:.1f} ADA to delegate.\n\n"
            f"--- POOL PARAMETERS (current round) ---\n{pool_state_summary}\n\n"
            f"--- USER DELEGATIONS (last round) ---\n{user_delegation_summary}\n\n"
            f"Saturation size per pool is {saturation_size:.1f} ADA.\n\n"
            "Rules:\n"
            "- Pools get no additional reward after saturation.\n"
            "- Margin reduces your share of the reward.\n"
            "- Higher pledge increases pool's reward (via a0).\n"
            "- You can split your stake across pools.\n\n"
            "Return a list of allocations (pool_id and stake_amount) that best maximize your expected reward."
        )

        structured_llm = self.llm.with_structured_output(UserMultiPoolReturnList)
        resp = structured_llm.invoke([HumanMessage(content=prompt)])
        self.stake_allocation = resp.allocations
