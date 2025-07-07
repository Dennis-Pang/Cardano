import json
import random
from langchain.schema import HumanMessage
from typing import List, Optional
from pydantic import BaseModel, Field, validator
import hashlib

class UserMultiPoolReturn(BaseModel):
    pool_id: int = Field(..., description="The pool id to delegate to")
    stake_amount: float = Field(..., description="The stake amount to delegate")

class UserMultiPoolReturnList(BaseModel):
    allocations: List[UserMultiPoolReturn]

# 全局决策缓存
_decision_cache = {}

# 导入配置
try:
    from constants import LLM_OPTIMIZATION
    _max_cache_size = LLM_OPTIMIZATION.get("MAX_USER_CACHE_SIZE", 100)
except ImportError:
    _max_cache_size = 100

class UserAgent:
    def __init__(self, user_id: int, stake: float, llm, persona: str, min_update_frequency: int = 3):
        self.user_id = user_id
        self.stake = stake
        self.llm = llm
        self.persona = persona
        self.stake_allocation: List[UserMultiPoolReturn] = []
        self.reward_history = []
        # 增加最小更新频率参数，使更新更保守
        base_frequency = self._get_update_frequency()
        self.update_frequency = max(base_frequency, min_update_frequency)
        self.last_update_round = -1
        self.last_decision_hash = None

    def _get_update_frequency(self) -> int:
        # 增加所有频率，使更新更保守
        frequencies = {
            "Decentralization Maximalist": 6,  # 从4增加到6
            "Mission-Driven Delegator": 15,   # 从10增加到15
            "Passive Yield-Seeker": 20,       # 从12增加到20
            "Active Yield-Farmer": 3,         # 从1增加到3
            "Brand Loyalist": 12,             # 从8增加到12
            "Risk-Averse Institutional": 10,  # 从6增加到10
        }
        return frequencies.get(self.persona, 8) # 默认从5增加到8

    def _get_decision_hash(self, pool_state_summary: str, user_delegation_summary: str) -> str:
        """生成决策上下文的哈希值，用于缓存相似决策"""
        context = f"{self.persona}:{self.stake}:{pool_state_summary}"
        return hashlib.md5(context.encode()).hexdigest()

    def _should_update(self, current_round: int, pool_state_summary: str, user_delegation_summary: str) -> bool:
        """决定是否需要更新策略"""
        # 如果没有初始分配，必须更新
        if not self.stake_allocation:
            return True
            
        # 检查更新频率
        if current_round - self.last_update_round < self.update_frequency:
            return False
            
        # 检查决策上下文是否有显著变化
        current_hash = self._get_decision_hash(pool_state_summary, user_delegation_summary)
        if current_hash == self.last_decision_hash:
            return False
            
        return True

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
        if not self._should_update(current_round, pool_state_summary, user_delegation_summary):
            return # Skip updating strategy this round

        # 检查缓存
        decision_hash = self._get_decision_hash(pool_state_summary, user_delegation_summary)
        if decision_hash in _decision_cache:
            cached_decision = _decision_cache[decision_hash]
            # 调整缓存决策以匹配当前stake
            self.stake_allocation = self._scale_allocation(cached_decision, self.stake)
            self.last_update_round = current_round
            self.last_decision_hash = decision_hash
            # 记录缓存命中
            from simulation import llm_call_stats
            llm_call_stats["cache_hits"] += 1
            return

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
        
        # 更新缓存
        if len(_decision_cache) >= _max_cache_size:
            # 移除最老的缓存项
            oldest_key = next(iter(_decision_cache))
            del _decision_cache[oldest_key]
        _decision_cache[decision_hash] = self.stake_allocation.copy()
        
        self.last_update_round = current_round
        self.last_decision_hash = decision_hash

    def _scale_allocation(self, allocation_template: List[UserMultiPoolReturn], target_stake: float) -> List[UserMultiPoolReturn]:
        """根据目标stake缩放分配"""
        total_template_stake = sum(a.stake_amount for a in allocation_template)
        if total_template_stake == 0:
            return allocation_template
            
        scale_factor = target_stake / total_template_stake
        return [
            UserMultiPoolReturn(
                pool_id=a.pool_id,
                stake_amount=a.stake_amount * scale_factor
            )
            for a in allocation_template
        ]
