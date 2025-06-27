# Cardano Stake Pool Simulation

This project simulates the behavior of Cardano stake pools and delegators in a multi-round environment. It models how users split their stake across multiple pools and how pool operators adjust their parameters to maximize profitability. The simulation uses an LLM (e.g., GPT-4o) to imitate decision-making processes of users and pool operators.

---

## 🔧 Features

- Simulates **multiple stake pools** with customizable pledge, margin, and cost.
- Models realistic **user delegation** behavior:
  - Users can split stake across **multiple pools**
  - Delegation decisions consider:
    - Pool saturation
    - Margin (operator profit cut)
    - Pledge (influences rewards via `a0`)
- Allows **pool operators** to update their parameters after each round.
- Broadcasts key information each round:
  - Current pool parameters (pledge, margin, cost)
  - Total stake delegated to each pool
  - Delegation distribution from previous round
  - Saturation size per pool
  - Rewards from the previous round
- Tracks **rewards** for users and **profits** for pools.
- Automatically saves output:
  - Human-readable `.txt` log
  - Structured `.json` file in `results/` folder (timestamped)

---

## 📦 Prerequisites

- Python 3.8 or newer
- An OpenAI API key with access to GPT-4 or GPT-4o

---

## 🛠 Installation

1. Clone the repository:

```bash
git clone [your-repository-url]
cd [repository-name]
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your-api-key-here
```

---

## ▶️ Usage

Run the simulation:

```bash
python main.py
```

This will:
- Create users and pools
- Simulate multiple rounds of delegation and reward distribution
- Let pools adapt parameters
- Save results in the `results/` directory:
  - `simulation_<timestamp>.json`
  - `simulation_<timestamp>.txt`

---

## ⚙️ Configuration

You can adjust simulation settings in `main.py` or `simulation.py`:

```python
sim_history = run_simulation(
    num_rounds=5,
    num_users=10,
    num_pools=3
)
```

You can also customize user stake distributions in `generate_powerlaw_stakes()`.

Total user funds are computed as:

```
total_funds = saturation_size * number_of_pools
```

---

## 📁 Output

All output is saved under the `results/` directory:

- `.json` file: structured data for further analysis or plotting
- `.txt` file: readable log of all simulation rounds, delegations, and rewards

---

## 📄 License

MIT License
