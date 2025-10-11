# Cardano Stake Pool Simulation

This project simulates a multi-round Cardano staking market where every participant is modelled as a single **Stakeholder**. Stakeholders may operate a pool, delegate to others, or do both. The engine implements the Shelley Reward Sharing Scheme (RSS), incorporates switching friction, applies pledge incentives, and tracks market concentration metrics (HHI, Nakamoto coefficient) each epoch. Results are streamed to disk so runs remain analyzable even if interrupted.

---

## 🚀 Quick Reference

- **Python version:** 3.13 (see `.venv/`)
- **Entry point:** `python main.py`
- **Outputs:** Timestamped folders under `results/`

---

## 📦 Environment Setup

1. **Clone the repository** (or drop the files into your workspace).
2. **Create / refresh the virtual environment** (Python 3.13):
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. **Optional configuration**  
   Create a `.env` file to override defaults (e.g., `CARDANO_MIGRATION_RATE`, `CARDANO_SHOCK_INTERVAL`, `CARDANO_REWARD_NOISE_STD`).

---

## 🧠 Round Structure

Each epoch executes the following sequence:

1. **Stake aggregation** – Stakeholders contribute pledge (if they operate a pool) and current delegations to build the pool stake table.
2. **Reward computation** – The Shelley Reward Sharing Scheme is evaluated using the configured `TOTAL_REWARDS`, `k = 1/ S_OPT`, and `a₀`. A light Gaussian noise term is applied to mimic network variability.
3. **Payout distribution** – Fixed costs and margins are deducted, the operator receives pledge-linked rewards, and delegators split the remaining pot proportionally.
4. **Behavioural updates** – A small migration cohort (default 5%) re-evaluates pools based on the latest net ROI. The rest remain inert, preserving realistic friction. Optional structural shocks (default every 50 rounds) tweak fees and costs.
5. **Metrics & persistence** – Logs are streamed to disk, concentration metrics (HHI, Nakamoto coefficient) are recorded, and a snapshot of pools/stakeholders is appended to `simulation_results.json`.

---

## ▶️ Running a Simulation

1. Activate the environment:
   ```bash
   source .venv/bin/activate
   ```
2. Launch the run with desired scale:
   ```bash
   python main.py --rounds 100 --users 300 --pools 100
   ```
   - `--rounds` – number of epochs (50–300 recommended)
  - `--users` – total stakeholders (operators + delegators)
   - `--pools` – number of pools (each backed by a stakeholder operator)
3. Inspect the generated `results/<timestamp>/` directory for the logs and JSON payload.
4. Optional: craft custom scripts to post-process the JSON or visualise trends.

---

## 🔧 Customisation Tips

- **Economics:** Tune `TOTAL_REWARDS`, `S_OPT`, and `A0` in `constants.py` to explore different decentralisation targets.
- **Behaviour knobs:** Override env vars such as `CARDANO_MIGRATION_RATE`, `CARDANO_IMPROVEMENT_THRESHOLD`, or `CARDANO_REWARD_NOISE_STD` to adjust cohort inertia and volatility.
- **Shock modelling:** Use `CARDANO_SHOCK_INTERVAL` and `CARDANO_SHOCK_COST_DELTA` to script structural events.
- **Data exports:** Extend `simulation.py` if you need additional metrics or alternative serialisation formats.

---

## ✅ Verification

- Compile check: `python -m compileall Cardano`

---

## 📄 License

MIT License

---

## 🇨🇳 中文对照指南

### 项目概述
本项目将所有参与者统一建模为 Stakeholder，涵盖开池者与普通委托人。在每个结算周期中，系统依据 Shelley Reward Sharing Scheme 计算奖励、考虑 pledge 激励与超饱和惩罚，并输出 HHI、Nakamoto 系数等集中度指标。

### 快速参考
- Python 版本：3.13（位于 `.venv/` 虚拟环境）
- 入口脚本：`python main.py`
- 输出目录：`results/` 下的时间戳子目录

### 环境配置步骤
1. 克隆仓库或将文件放入工作目录。
2. 创建并激活 Python 3.13 虚拟环境，安装依赖：
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. （可选）在 `.env` 中写入参数，例如 `CARDANO_MIGRATION_RATE`、`CARDANO_SHOCK_INTERVAL`。

### 轮次流程
1. 汇总质押：池运营者投入 pledge，所有 Stakeholder 的委托写入当前池的总质押。
2. 计算奖励：调用 Shelley RSS 公式，并加入轻度噪声模拟网络波动。
3. 发放收益：扣除固定成本和 margin，运营者获得 pledge 奖励，其余按份额分配给委托人。
4. 行为更新：仅约 5% 委托人重新评估池子，其余保持原状；可配置的结构性冲击每隔若干轮触发。
5. 指标输出：记录 HHI、Nakamoto 等集中度指标，并实时写入日志与 JSON。

### 运行仿真
```bash
source .venv/bin/activate
python main.py --rounds 100 --users 300 --pools 100
```
参数含义：`--rounds` 为轮次数（建议 50–300），`--users` 表示 Stakeholder 总数（包含运营者），`--pools` 为质押池数量。运行过程中日志会实时写入磁盘，可在中断后继续分析。

### 自定义建议
- **经济参数**：在 `constants.py` 中调整 `TOTAL_REWARDS`、`S_OPT`、`A0`。
- **行为参数**：通过环境变量（如 `CARDANO_MIGRATION_RATE`、`CARDANO_IMPROVEMENT_THRESHOLD`、`CARDANO_REWARD_NOISE_STD`）修改迁移率、收益噪声。
- **冲击设置**：`CARDANO_SHOCK_INTERVAL`、`CARDANO_SHOCK_COST_DELTA` 用于控制结构性冲击。
- **扩展输出**：可按需修改 `simulation.py` 增加额外指标或数据导出。

### 验证步骤
- 语法检查：`python -m compileall Cardano`

### 许可证
MIT 许可协议
