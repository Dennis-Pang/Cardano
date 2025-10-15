# Cardano Stake Pool Simulation

This repository contains a multi-round simulation of Cardano stake pools and delegators powered by large language models (LLMs). Pool operators adjust their parameters in response to market signals, delegators rebalance their stake, and the simulation records the resulting network dynamics round by round.

---

## 🚀 At a Glance
- Multi-round environment where delegators and pool operators react to shared network briefings.
- Pool operators and delegators are persona-driven agents that call an OpenAI-compatible LLM to justify and execute their decisions.
- Delegator wealth follows a configurable power-law distribution; stake can be split across multiple pools every round.
- Each run logs full round transcripts, JSON state history, and inequality metrics (Gini coefficients) for later analysis.

---

## 📂 Project Layout
- `main.py` – CLI entry point; parses arguments and starts a simulation run.
- `simulation.py` – Orchestrates rounds, builds network briefings, aggregates rewards, and streams logs/results to `results/<timestamp>/`.
- `pool_agents.py` – Persona-aware stake pool operators that revise pledge, margin, and cost after each round via an LLM call.
- `user_agents.py` – Delegator personas that decide how to split stake across pools. Ensure this module is available before running the simulation.
- `constants.py` – Network-wide parameters (`TOTAL_REWARDS`, `S_OPT`, `A0`) used in the Cardano reward formula.

---

## 📦 Requirements
- Python 3.10 or newer.
- Dependencies listed in `requirements.txt` (`pip install -r requirements.txt`).  
  If your `user_agents.py` relies on `pydantic`, install it alongside the listed packages.
- An OpenAI-compatible endpoint. By default the code targets a local Ollama server.

---

## 🔧 Setup
1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd Cardano
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure environment variables**  
   Create a `.env` file in the repository root (or export the variables in your shell):
   ```env
   OLLAMA_BASE_URL=http://localhost:11434/v1
   OLLAMA_API_KEY=ollama
   OLLAMA_MODEL=qwen2.5:7b-instruct
   LLM_TEMPERATURE=0.0
   ```
   To use OpenAI or another provider, set `OLLAMA_BASE_URL` to the service URL and provide the corresponding API key.

---

## ▶️ Run a Simulation
```bash
python main.py --rounds 10 --users 50 --pools 5
```
- `--rounds` – number of epochs to simulate (default `2`).
- `--users` – delegator count (default `2`).
- `--pools` – active stake pools (default `2`).

Each delegator and pool operator triggers an LLM request per decision, so larger runs can take time and consume credits when using paid endpoints.

---

## 📊 Outputs
Every run creates a timestamped folder under `results/`, e.g. `results/20251015-104646/`, containing:
- `simulation_log.txt` – human-readable round summaries, briefings, and agent actions.
- `simulation_results.json` – structured state snapshots per round, including allocations, rewards, and Gini metrics.

The console also streams delegation decisions and the latest inequality metrics to help monitor long simulations.

---

## ⚙️ Customize the Model
- **CLI parameters** – Adjust rounds, users, and pools per invocation.
- **Network constants** – Tweak `TOTAL_REWARDS`, `S_OPT`, and `A0` in `constants.py` to explore alternative reward curves.
- **Stake distribution** – Update `generate_powerlaw_stakes` in `simulation.py` (alpha, min/max stake, seed) to change the initial wealth profile.
- **Agent personas** – Edit persona weights/prompts in `simulation.py`, `user_agents.py`, and `pool_agents.py` to model new behaviors.
- **LLM configuration** – Override `OLLAMA_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_API_KEY`, or `LLM_TEMPERATURE` in the environment.

---

## ❗️ Notes
- The simulation is synchronous and runs entirely on the local machine; provide a responsive LLM endpoint to keep rounds moving.
- Logs are rewritten after each round to avoid partial files; keep the process running until completion to capture the full history.
- The repository ignores the `results/` directory by default. Add generated artifacts to version control only if you need to share them.

---

## 📄 License
MIT License

---

# 卡尔达诺质押池模拟

该仓库实现了一个依赖大语言模型的多轮 Cardano 质押池模拟。质押池运营者会根据市场信号调整参数，委托者会重新分配质押，系统逐轮记录网络动态。

---

## 🚀 核心特点
- 多轮博弈环境：委托者与运营者都会响应网络通报做出决策。
- 质押池与委托者均由设定的人格驱动，通过 OpenAI 兼容接口调用 LLM 给出理由与操作。
- 委托者初始资产遵循可配置的幂律分布，并可在每轮把筹码拆分到多个池。
- 每次运行都会生成日志、结构化 JSON 历史，以及用于衡量不平等的 Gini 系数。

---

## 📂 目录结构
- `main.py`：命令行入口，解析参数并启动模拟。
- `simulation.py`：统筹每一轮，构建网络通报，汇总奖励，并把结果写入 `results/<timestamp>/`。
- `pool_agents.py`：基于人格的质押池运营者，借助 LLM 调整 pledge、margin 与 cost。
- `user_agents.py`：委托者人格与分配策略实现。运行前请确认该模块可用。
- `constants.py`：Cardano 奖励公式所需的网络常量（`TOTAL_REWARDS`、`S_OPT`、`A0`）。

---

## 📦 环境要求
- Python 3.10 及以上版本。
- 运行 `pip install -r requirements.txt` 安装依赖。  
  如果 `user_agents.py` 用到了 `pydantic`，请额外安装该库。
- 一个 OpenAI 兼容的推理接口；默认使用本地 Ollama 服务。

---

## 🔧 初始化
1. **克隆仓库**
   ```bash
   git clone <repo-url>
   cd Cardano
   ```
2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```
3. **配置环境变量**  
   在仓库根目录创建 `.env`（或直接在 shell 中导出）：
   ```env
   OLLAMA_BASE_URL=http://localhost:11434/v1
   OLLAMA_API_KEY=ollama
   OLLAMA_MODEL=qwen2.5:7b-instruct
   LLM_TEMPERATURE=0.0
   ```
   如需调用 OpenAI 等外部服务，请将 `OLLAMA_BASE_URL` 改为对应地址并提供有效的 API Key。

---

## ▶️ 运行模拟
```bash
python main.py --rounds 10 --users 50 --pools 5
```
- `--rounds`：模拟轮数（默认 `2`）。
- `--users`：委托者数量（默认 `2`）。
- `--pools`：质押池数量（默认 `2`）。

每位委托者与运营者在每轮都会触发一次 LLM 请求，规模较大的实验需要更多时间与算力（或 API 额度）。

---

## 📊 输出结果
运行结束后会在 `results/` 下生成时间戳目录（例如 `results/20251015-104646/`），包含：
- `simulation_log.txt`：便于阅读的轮次记录、广播内容与代理行为。
- `simulation_results.json`：结构化的轮次快照，涵盖委托分配、奖励与 Gini 指标。

命令行会实时输出委托分配与最新的 Gini 系数，方便监控长时间运行的实验。

---

## ⚙️ 自定义选项
- **命令行参数**：按需调整轮数、用户和质押池数量。
- **网络常量**：在 `constants.py` 修改 `TOTAL_REWARDS`、`S_OPT`、`A0` 以探索不同奖励曲线。
- **筹码分布**：在 `simulation.py` 的 `generate_powerlaw_stakes` 中调整幂律参数、最小/最大值与随机种子。
- **人格与提示词**：在 `simulation.py`、`user_agents.py`、`pool_agents.py` 中修改人格比例和提示内容。
- **LLM 设置**：通过环境变量覆盖 `OLLAMA_MODEL`、`OLLAMA_BASE_URL`、`OLLAMA_API_KEY`、`LLM_TEMPERATURE`。

---

## ❗️ 使用提示
- 模拟为同步执行，需要稳定、响应快的 LLM 服务以保证每轮顺利运行。
- 日志文件会在每轮结束后整体重写；请在运行结束后再读取结果以避免截断。
- 仓库默认忽略 `results/`；若需共享实验产出，可自行把需要的文件纳入版本控制。

---

## 📄 许可证
MIT License
