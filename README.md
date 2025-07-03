# Cardano Stake Pool Simulation

This project simulates the behavior of Cardano stake pools and delegators in a multi-round environment. It models how users with different personas split their stake and how pool operators with different strategies adjust their parameters to maximize profitability. The simulation uses an LLM (e.g., GPT-4o) to imitate the decision-making processes of these agents.

---

## 🔧 Features

-   **Realistic Agent Personas**: Simulates a diverse ecosystem of delegators and pool operators with distinct motivations, risk profiles, and engagement levels based on real-world observations.
-   **Configurable Simulation**: Easily configure rounds, user/pool counts, and persona distributions via command-line arguments.
-   **Nuanced Delegation Logic**: Models complex behaviors from profit-chasing and decentralization support to brand loyalty and risk aversion.
-   **Adaptive Operators**: Pool operators with different business strategies (e.g., `Community Builder`, `Profit Maximizer`) periodically update their parameters.
-   **Cost-Efficient**: Agents only update their strategy periodically based on their persona, reducing LLM calls and simulation costs.
-   **Detailed Logging**: Saves a human-readable `.txt` log and a structured `.json` file for deep analysis.
-   **Built-in Analysis**: Includes a script to automatically generate charts from the simulation output, visualizing market dynamics, profitability, and wealth distribution.

---

## 📦 Prerequisites

-   Python 3.8 or newer
-   An OpenAI API key with access to a model like GPT-4o.

---

## 🛠 Installation

1.  **Clone the repository:**
    ```bash
    git clone [your-repository-url]
    cd [repository-name]
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Create a `.env` file** in the project root and add your API key:
    ```env
    OPENAI_API_KEY=your-api-key-here
    ```

---

## ▶️ Usage

1.  **Run the simulation** from the command line:
    ```bash
    python main.py --rounds 10 --users 50 --pools 5
    ```
    -   `--rounds`: Number of simulation rounds.
    -   `--users`: Number of delegators.
    -   `--pools`: Number of stake pools.

    This will generate a timestamped subfolder inside the `results/` directory (e.g., `results/20250629-170603/`). Inside this folder, you will find:
    -   `simulation_log.txt`
    -   `simulation_results.json`

2.  **Analyze the results** by pointing the analysis script to the generated folder:
    ```bash
    python analyze.py results/20250629-170603
    ```
    This will create an `analysis_chart.png` file inside that same folder, visualizing the simulation dynamics.

---

## ⚙️ Configuration

-   **Simulation Parameters**: Adjust rounds, users, and pools using the command-line arguments shown above.
-   **Agent Personas**: You can modify the persona lists and their associated behaviors (prompts and update frequencies) in `user_agents.py` and `pool_agents.py`.
-   **Network Constants**: Core Cardano parameters like `TOTAL_REWARDS`, `S_OPT` (saturation size), and `A0` (pledge influence) can be modified in `constants.py`.

---

## 📁 Output

All output is saved in the `results/` directory:

-   `.txt`: A human-readable log of all rounds, agent actions, and outcomes.
-   `.json`: Structured data for programmatic analysis.
-   `.png`: A chart summarizing the key results of the simulation.

---

## 📄 License

MIT License
