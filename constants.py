# Network parameters
TOTAL_REWARDS = 1_000_000  # Total rewards per epoch
S_OPT = 64_000_000  # Optimal saturation size
A0 = 0.3  # Pledge influence factor

# LLM优化配置
LLM_OPTIMIZATION = {
    # 最小更新频率（轮数）
    "MIN_USER_UPDATE_FREQUENCY": 3,
    "MIN_POOL_UPDATE_FREQUENCY": 4,
    
    # 缓存设置
    "MAX_USER_CACHE_SIZE": 100,
    "MAX_POOL_CACHE_SIZE": 50,
    
    # 批处理设置
    "ENABLE_BATCH_PROCESSING": True,
    "BATCH_SIZE": 10,
    
    # 智能更新阈值
    "STAKE_CHANGE_THRESHOLD": 0.1,  # 10%的stake变化才触发更新
    
    # 频率倍增器（用于进一步减少调用）
    "FREQUENCY_MULTIPLIER": 1.5,
}
