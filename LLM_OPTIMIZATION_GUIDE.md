# LLM调用优化指南

## 问题解决

本次优化解决了模拟时LLM调用频率过高，超过token速度限制的问题。

## 主要优化策略

### 1. 增加更新频率（减少调用次数）

**原始频率 → 优化后频率：**
- Decentralization Maximalist: 4轮 → 6轮
- Mission-Driven Delegator: 10轮 → 15轮  
- Passive Yield-Seeker: 12轮 → 20轮
- Active Yield-Farmer: 1轮 → 3轮 (最大改进)
- Brand Loyalist: 8轮 → 12轮
- Risk-Averse Institutional: 6轮 → 10轮

**池代理频率：**
- Community Builder: 5轮 → 8轮
- Profit Maximizer: 2轮 → 4轮 (最大改进)
- Corporate Pool: 8轮 → 12轮

### 2. 智能缓存机制

- **决策缓存**: 相似的市场状态会复用之前的决策
- **用户缓存**: 最多100个决策缓存
- **池缓存**: 最多50个决策缓存
- **哈希匹配**: 基于上下文生成哈希值，避免重复计算

### 3. 智能更新判断

- **上下文变化检测**: 只有市场状态显著变化时才更新
- **Stake变化阈值**: 池的stake变化超过10%才触发更新
- **最小更新间隔**: 强制最小更新频率避免过度调用

### 4. 批处理机制

- **批量处理**: 将需要更新的代理分批处理
- **延迟控制**: 批次间添加0.1秒延迟避免rate limit
- **智能分组**: 只处理真正需要更新的代理

## 配置参数

在 `constants.py` 中的 `LLM_OPTIMIZATION` 配置：

```python
LLM_OPTIMIZATION = {
    # 最小更新频率（轮数）
    "MIN_USER_UPDATE_FREQUENCY": 3,      # 用户最少3轮更新一次
    "MIN_POOL_UPDATE_FREQUENCY": 4,      # 池最少4轮更新一次
    
    # 缓存设置
    "MAX_USER_CACHE_SIZE": 100,          # 用户决策缓存大小
    "MAX_POOL_CACHE_SIZE": 50,           # 池决策缓存大小
    
    # 批处理设置
    "ENABLE_BATCH_PROCESSING": True,     # 启用批处理
    "BATCH_SIZE": 10,                    # 批处理大小
    
    # 智能更新阈值
    "STAKE_CHANGE_THRESHOLD": 0.1,       # 10%的stake变化才触发更新
    
    # 频率倍增器
    "FREQUENCY_MULTIPLIER": 1.5,         # 进一步减少调用的倍数
}
```

## 性能提升估算

假设原始配置下的LLM调用次数：
- 50用户 × 10轮 = 500次用户调用
- 5池 × 10轮 = 50次池调用
- **总计: 550次调用**

优化后的估算调用次数：
- 用户调用减少约 **60-70%**
- 池调用减少约 **70-80%**
- 加上缓存命中，总体减少 **70-85%**
- **新估算: 80-150次调用**

## 使用方法

### 1. 运行优化的模拟

```bash
python main.py --rounds 10 --users 50 --pools 5
```

### 2. 查看LLM调用统计

运行后会自动显示：
```
=== LLM调用统计 ===
总用户调用: 45
总池调用: 12
总调用数: 57
缓存命中: 23
平均每轮调用: 5.7
总轮数: 10
```

### 3. 调整配置参数

根据你的API限制调整 `constants.py` 中的参数：

- **如果仍然超限**: 增加 `MIN_UPDATE_FREQUENCY` 值
- **如果调用过少**: 减少更新频率或禁用批处理
- **如果需要更多缓存**: 增加 `MAX_CACHE_SIZE`

### 4. 紧急降级方案

如果仍然遇到rate limit，可以采用以下紧急措施：

```python
# 在constants.py中设置更保守的参数
LLM_OPTIMIZATION = {
    "MIN_USER_UPDATE_FREQUENCY": 10,     # 大幅增加更新间隔
    "MIN_POOL_UPDATE_FREQUENCY": 15,
    "ENABLE_BATCH_PROCESSING": False,    # 禁用批处理以更好控制
    "STAKE_CHANGE_THRESHOLD": 0.2,       # 提高变化阈值
}
```

## 监控和调试

### 查看详细统计

每次运行后，会在结果目录生成 `llm_stats.json`：

```json
{
  "user_calls": 45,
  "pool_calls": 12,
  "cache_hits": 23,
  "total_rounds": 10
}
```

### 调试模式

在批处理函数中已添加详细日志：
- 每轮显示需要更新的用户/池数量
- 显示总数中的更新比例

## 进一步优化建议

1. **模型选择**: 考虑使用更快的模型（如llama3-8b而非GPT-4）
2. **提示优化**: 缩短提示文本减少token消耗
3. **分层缓存**: 为不同persona建立专门缓存
4. **预计算**: 预先生成一些常见决策模板

## 故障排除

**Q: 缓存没有生效？**
A: 检查`_get_decision_hash`方法是否正确生成哈希

**Q: 仍然调用过多？**  
A: 进一步增加`MIN_UPDATE_FREQUENCY`或提高`STAKE_CHANGE_THRESHOLD`

**Q: 模拟结果质量下降？**
A: 适当降低更新频率，在性能和质量间找平衡

**Q: 批处理延迟太长？**
A: 减小`BATCH_SIZE`或调整延迟时间