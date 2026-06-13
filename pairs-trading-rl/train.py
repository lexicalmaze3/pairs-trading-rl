import argparse
import os
import sys
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.utils import set_random_seed
from env import PairsTradingEnv
from evaluate import run_episode

# Print UTF-8 so decorative characters don't crash on Windows when redirected.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Train a PPO agent on one cointegrated pair.")
    parser.add_argument("--ticker1",    default="GLD",     help="First ticker")
    parser.add_argument("--ticker2",    default="RTX",     help="Second ticker")
    parser.add_argument("--timesteps",  default=200_000,   type=int)
    parser.add_argument("--start",      default="2023-01-01")
    parser.add_argument("--end",        default="2025-01-01")
    parser.add_argument("--seed",       default=42, type=int, help="Random seed")
    args = parser.parse_args()

    set_random_seed(args.seed)
    model_path = os.path.join(MODEL_DIR, f"pairs_ppo_{args.ticker1}_{args.ticker2}")

    env = PairsTradingEnv(
        start_date=args.start,
        end_date=args.end,
        ticker1=args.ticker1,
        ticker2=args.ticker2,
    )

    model = PPO(
        "MlpPolicy",
        env,
        n_steps=2048,
        batch_size=64,
        ent_coef=0.02,
        seed=args.seed,
        verbose=1,
    )

    model.learn(total_timesteps=args.timesteps)
    model.save(model_path)
    print(f"\nModel saved to {model_path}.zip")

    # In-sample sanity check on realized P&L (NOT a performance claim — use
    # walk_forward.py for an honest out-of-sample evaluation).
    eval_env = PairsTradingEnv(
        start_date=args.start,
        end_date=args.end,
        ticker1=args.ticker1,
        ticker2=args.ticker2,
    )
    steps, trades = run_episode(model, eval_env)
    daily = np.array([s["pnl"] for s in steps], dtype=float)
    sharpe = (daily.mean() / daily.std() * np.sqrt(252)) if daily.std() > 0 else 0.0

    print("\nIn-sample check (realized P&L, net of costs — overfit, illustrative only):")
    print(f"  Trades       : {len(trades)}")
    print(f"  Total P&L    : {daily.sum():.4f}  (spread units)")
    print(f"  Sharpe (ann.): {sharpe:.4f}")
    print("  -> Evaluate out-of-sample with: python walk_forward.py")


if __name__ == "__main__":
    main()
