import argparse
from simulation import run_simulation

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a Cardano stake pool simulation.")
    parser.add_argument("--rounds", type=int, default=20, help="Number of simulation rounds.")
    parser.add_argument("--users", type=int, default=50, help="Number of users.")
    parser.add_argument("--pools", type=int, default=10, help="Number of stake pools.")
    args = parser.parse_args()

    sim_history = run_simulation(
        num_rounds=args.rounds,
        num_users=args.users,
        num_pools=args.pools
    )
