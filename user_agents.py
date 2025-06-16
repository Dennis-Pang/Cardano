import json
from langchain.schema import HumanMessage
from typing import List
from pool_agents import PoolAgent
from pydantic import BaseModel, Field

class UserAgent:
    def __init__(self, user_id: int, stake: float, llm):
        self.user_id = user_id
        self.stake = stake
        self.llm = llm
        self.delegated_pool = None
        self.reward_history = []

    def choose_pool(self, pools: List[PoolAgent], max_stake: float = 10000):
        pools_summary = "\n".join(
            [f"Pool {p.pool_id}: pledge={p.pledge:.1f}, margin={p.margin:.2f}, cost={p.cost:.1f}, total_stake={p.stake_delegated + p.pledge:.1f}"
            for p in pools]
        )
        prompt = (
            f"You have up to {max_stake:.1f} ADA to delegate.\n"
            f"Given these pools:\n{pools_summary}\n"
            "Reply the pool id to delegate to and the stake amount to delegate to maximize your reward.\n"
        )

        structured_llm = self.llm.with_structured_output(UserAgentReturn)
        resp = structured_llm.invoke([HumanMessage(content=prompt)])
        pool_id, stake_amount = resp.pool_id, resp.stake_amount
        
        if stake_amount > max_stake:
            stake_amount = max_stake
        if any(p.pool_id == pool_id for p in pools):
            self.delegated_pool = pool_id
            self.stake = stake_amount
        else:
            raise ValueError(f"Pool {pool_id} not found")

class UserAgentReturn(BaseModel):
    pool_id: int = Field(..., description="The pool id to delegate to")
    stake_amount: float = Field(..., description="The stake amount to delegate")