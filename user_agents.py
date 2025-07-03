import json
import random
from langchain.schema import HumanMessage
from typing import List
from pydantic import BaseModel, Field, validator

class UserMultiPoolReturn(BaseModel):
    pool_id: int = Field(..., description="The pool id to delegate to")
    stake_amount: float = Field(..., description="The stake amount to delegate")

class UserMultiPoolReturnList(BaseModel):
    allocations: List[UserMultiPoolReturn]

class UserAgent:
    def __init__(self, user_id: int, stake: float, llm, persona: str):
        self.user_id = user_id
        self.stake = stake
        self.llm = llm
        self.persona = persona
        self.stake_allocation: List[UserMultiPoolReturn] = []
        self.reward_history = []
        self.update_frequency = self._get_update_frequency()

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

    def _get_persona_prompt(self) -> str:
        prompts = {
            "Decentralization Maximalist": "Your primary goal is to strengthen the Cardano network. You prioritize delegating to single-pool operators to counter centralization. You prefer pools that are far from saturation. While you want fair returns, you will accept a slightly lower ROA to support a small, independent, high-quality operator.",
            "Mission-Driven Delegator": "You are loyal to a cause. You delegate to pools that fund charities, environmental projects, or build tools for the ecosystem. Your choice is almost entirely based on the pool's mission, provided its performance isn't terrible. You rarely change your delegation.",
            "Passive Yield-Seeker": "You want to earn rewards with minimal effort. You likely chose a pool from the top of a ranking list and will only change it if it becomes saturated or its fees increase dramatically. You prefer a 'set-it-and-forget-it' approach.",
            "Active Yield-Farmer": "Your only goal is to maximize ROA. You constantly monitor pool performance, including luck factor and saturation, and will switch frequently to gain even a small edge. You are highly analytical and use all available data to make your decision.",
            "Brand Loyalist": "You delegate to operators you know and trust from the community (e.g., developers, educators, content creators). Your decision is based on the operator's reputation and communication. You trust them to run a fair and performant pool and will stick with them unless their performance severely degrades.",
            "Risk-Averse Institutional": "You prioritize secure, stable, and predictable returns. You strongly prefer large, established pools with a high pledge, a long track record of reliability, and low saturation. You will not delegate to new or unproven pools."
        }
        return prompts.get(self.persona, "You are a standard delegator trying to get a good return on your stake.")

    def choose_pools(
        self,
        pool_state_summary: str,
        user_delegation_summary: str,
        saturation_size: float,
        current_round: int
    ):
        if current_round % self.update_frequency != 0 and self.stake_allocation:
            return # Skip updating strategy this round

        prompt = (
            f"You are a Cardano user with {self.stake:.1f} ADA to delegate.\n"
            f"Your persona is: {self.persona}. {self._get_persona_prompt()}\n\n"
            f"--- POOL PARAMETERS (current round) ---\n{pool_state_summary}\n\n"
            f"--- USER DELEGATIONS (last round) ---\n{user_delegation_summary}\n\n"
            f"Saturation size per pool is {saturation_size:.1f} ADA.\n\n"
            "Rules:\n"
            "- Pools get no additional reward after saturation.\n"
            "- Margin reduces your share of the reward.\n"
            "- Higher pledge increases pool's reward (via a0).\n"
            "- You can split your stake across pools.\n\n"
            "Return a list of allocations (pool_id and stake_amount) that best match your persona's goal."
        )

        structured_llm = self.llm.with_structured_output(UserMultiPoolReturnList)
        resp = structured_llm.invoke([HumanMessage(content=prompt)])
        self.stake_allocation = resp.allocations
