# Cardano Stake Pool Simulation

This project simulates the behavior of Cardano stake pools and delegators in a multi-round environment. It models how users choose stake pools and how pool operators adjust their parameters to maximize profits.

## Features

- Simulates multiple stake pools with different parameters (pledge, margin, cost)
- Models user delegation behavior
- Tracks rewards and profits for both pools and users
- Uses OpenAI's GPT model for decision-making

## Prerequisites

- Python 3.8+
- OpenAI API key

## Installation

1. Clone the repository:
```bash
git clone [your-repository-url]
cd [repository-name]
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your OpenAI API key:
   - Create a `.env` file in the project root
   - Add your API key: `OPENAI_API_KEY=your-api-key-here`

## Usage

Run the simulation:
```bash
python simulation.py
```

The simulation will:
1. Create multiple stake pools with random initial parameters
2. Simulate user delegation decisions
3. Calculate rewards and profits
4. Print detailed results for each round

## Configuration

You can modify the following parameters in `simulation.py`:
- `num_rounds`: Number of simulation rounds
- `num_users`: Number of users participating
- `num_pools`: Number of stake pools

## License

MIT License 