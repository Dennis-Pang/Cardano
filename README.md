# Cardano Stake Pool Simulation

This project simulates a multi-round market where Cardano delegators and stake-pool operators evolve strategies with the help of a locally hosted LLM served from Ollama. Each agent reasons about noisy recent performance, produces structured text outputs, and follows built-in behavioural guardrails (limited memory, switching friction, conservative fee adjustments). The repository includes data logging utilities and analysis helpers for inspecting the simulation trails.

---

## 🚀 Quick Reference

- **Python version:** 3.13 (see `.venv/`)
- **LLM backend:** Local Ollama model (`OLLAMA_MODEL` env var, default `llama3`)
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
3. **Start Ollama** (if not already running):
   ```bash
   ollama serve
   ```
4. **Pull the model** you plan to use (defaults to `llama3`). For other choices set `OLLAMA_MODEL` in your shell or `.env`:
   ```bash
   ollama pull llama3
   export OLLAMA_MODEL=llama3
   ```
5. **Populate `.env`** (optional). The simulation loads `.env` automatically, so set extra knobs here (e.g., `OLLAMA_MODEL`, custom run identifiers).

---

## 🧠 Agent Workflow Overview

The simulation coordinates users (delegators) and pool operators across repeated rounds. At each round:

1. **Summaries Compile**
   - Pool and user states are aggregated into natural language summaries (stake, rewards, margins, etc.).

2. **Delegator Decisions** (`user_agents.py`)
   - Every cohort receives a system prompt describing its persona, limited to a rolling history window and explicit switching friction.
   - The user prompt provides current pool metrics, the last few rounds of earnings, and a brief record of prior allocations.
   - The Ollama model replies with:
     ```
     THOUGHT: ...reasoning...
     SELECTIONS: POOL1::value, POOL2::value
     ```
   - A regex parser extracts `POOLn::amount` pairs and stores them as JSON for downstream accounting. Most rounds only a small share of cohorts rebalance, matching the configured migration rate.

3. **Pool Operator Updates** (`pool_agents.py`)
   - Similar structure, but the system prompt enforces ≤5% parameter tweaks and acknowledges noisy telemetry.
   - LLM-managed pools respond with:
     ```
     THOUGHT: ...analysis...
     PARAMS: PLEDGE::value, MARGIN::value, COST::value
     ```
   - Parsed values adjust the pool’s configuration for the next epoch (clamped to the small-step policy); invalid responses fall back to the previous settings.

4. **Reward & Profit Calculation** (`simulation.py`)
   - Delegated stake totals feed into Cardano-inspired reward formulas using `TOTAL_REWARDS`, `S_OPT`, and `A0`, then a light 1% Gaussian noise is injected to mimic real-world volatility.
   - User rewards and pool profits are recorded; agents append round outcomes to their limited histories.

5. **Structural Events**
   - Every configurable interval (default 50 rounds) a “shock” nudges fees upward and trims rewards, forcing strategies to re-evaluate.

6. **Persistence**
   - Each run streams logs to `results/<timestamp>/simulation_log.txt` and continuously refreshes `simulation_results.json`, so partial progress survives interruptions.
     - `simulation_log.txt` – human-readable round-by-round trace (thoughts, decisions, rewards).
     - `simulation_results.json` – structured data for external analysis pipelines.

---

## ▶️ Running a Simulation

1. Activate the environment:
   ```bash
   source .venv/bin/activate
   ```
2. Launch the run with desired scale:
   ```bash
   python main.py --rounds 100 --users 30 --pools 80
   ```
   - `--rounds` – number of epochs (50–300 recommended)
   - `--users` – delegator cohorts (treat as grouped users, default 30)
   - `--pools` – stake pools (only a subset may use LLM-driven strategies)
3. Inspect the generated `results/<timestamp>/` directory for the logs and JSON payload.
4. Optional: craft custom scripts to post-process the JSON or visualise trends.

---

## 🔧 Customisation Tips

- **Model Choice:** Set `OLLAMA_MODEL` (env or `.env`) to switch to another local model.
- **Persona Prompts:** Adjust persona text and message templates inside `prompts.py`; tweak update frequencies or migration probabilities in `user_agents.py` / `pool_agents.py` if your cohorts need different inertia levels.
- **Economics:** Modify constants in `constants.py` to explore alternative network reward parameters.
- **Environment Knobs:** Override defaults via env vars (e.g., `CARDANO_USER_HISTORY_WINDOW`, `CARDANO_REWARD_NOISE_STD`, `CARDANO_SHOCK_INTERVAL`) to explore different market frictions.
- **Logging:** Extend `simulation.py` to capture extra telemetry (e.g., raw thoughts) if you need richer analytics.

---

## ✅ Verification

- Compile check: `python -m compileall Cardano`
- LLM availability: `curl http://localhost:11434/api/tags` (ensures Ollama is serving models)

---

## 📄 License

MIT License

---

## 🇨🇳 中文对照指南

### 项目概述
本项目利用部署在本地的 Ollama 模型，模拟 Cardano 委托人和质押池运营者在多轮市场中的策略演化。每位智能体只基于最近窗口的噪声数据进行分析，输出固定格式的文本，并遵循内置的行为约束（迁移摩擦、小步调参等）。

### 快速参考
- Python 版本：3.13（位于 `.venv/` 虚拟环境）
- 模型后端：本地 Ollama（通过环境变量 `OLLAMA_MODEL` 指定，默认 `llama3`）
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
3. 启动 Ollama 服务：`ollama serve`
4. 拉取所需模型并设置环境变量（如 `OLLAMA_MODEL=llama3`）。
5. 可在 `.env` 中配置额外参数，程序会自动加载。

### 智能体工作流
1. 生成当前轮次的池子和用户摘要。
2. 委托人根据系统提示、人设和历史记录，输出 `THOUGHT` 与 `SELECTIONS`，程序用正则解析 `POOLn::数值`。
3. 质押池运营者输出 `THOUGHT` 与 `PARAMS`，解析出新的 pledge、margin、cost。
4. `simulation.py` 按 Cardano 奖励公式计算收益与利润，并写入历史。
5. 每隔固定轮次触发结构性冲击（默认 50 轮），例如手续费上调或收益下调，促使策略重新评估。
6. 生成日志与 JSON 数据，保存在 `results/<timestamp>/`。

### 运行仿真
```bash
source .venv/bin/activate
python main.py --rounds 100 --users 30 --pools 80
```
参数含义：`--rounds` 为轮次数（建议 50–300），`--users` 表示委托人群组数量，`--pools` 为质押池数量。运行过程中日志会实时写入磁盘，可在中断后继续分析。

### 自定义建议
- 修改 `OLLAMA_MODEL` 以切换本地模型。
- 提示文案集中在 `prompts.py`，可根据需求修改；若想调整不同人群的惯性或更新频率，可在 `user_agents.py`、`pool_agents.py` 中修改相关参数。
- 在 `constants.py` 中修改经济参数，例如 `TOTAL_REWARDS`、`S_OPT`、`A0`。
- 可通过环境变量（如 `CARDANO_USER_HISTORY_WINDOW`、`CARDANO_REWARD_NOISE_STD`、`CARDANO_SHOCK_INTERVAL`）调节记忆窗口、噪声和冲击频率。
- 如需更多日志，可扩展 `simulation.py`。

### 验证步骤
- 语法检查：`python -m compileall Cardano`
- 确认模型服务：`curl http://localhost:11434/api/tags`

### 许可证
MIT 许可协议
