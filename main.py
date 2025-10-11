import argparse
from simulation import run_simulation

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a Cardano stake pool simulation.")
    parser.add_argument("--rounds", type=int, default=100, help="Number of simulation rounds (epochs).")
    parser.add_argument("--users", type=int, default=30, help="Number of delegator cohorts.")
    parser.add_argument("--pools", type=int, default=80, help="Number of stake pools.")
    args = parser.parse_args()

    sim_history = run_simulation(
        num_rounds=args.rounds,
        num_users=args.users,
        num_pools=args.pools
    )
