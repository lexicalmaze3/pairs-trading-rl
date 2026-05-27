import argparse
import os
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy
from env import PairsTradingEnv

MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker1",    default="GLD",     help="First ticker")
    parser.add_argument("--ticker2",    default="RTX",     help="Second ticker")
    parser.add_argument("--timesteps",  default=200_000,   type=int)
    parser.add_argument("--start",      default="2023-01-01")
    parser.add_argument("--end",        default="2025-01-01")
    args = parser.parse_args()

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
        verbose=1,
    )

    model.learn(total_timesteps=args.timesteps)
    model.save(model_path)
    print(f"\nModel saved to {model_path}.zip")

    eval_env = PairsTradingEnv(
        start_date=args.start,
        end_date=args.end,
        ticker1=args.ticker1,
        ticker2=args.ticker2,
    )
    episode_rewards, _ = evaluate_policy(
        model, eval_env,
        n_eval_episodes=10,
        return_episode_rewards=True,
    )

    mean_r = np.mean(episode_rewards)
    std_r  = np.std(episode_rewards)
    sharpe = mean_r / std_r if std_r > 0 else 0.0

    print(f"\nEval over 10 episodes:")
    print(f"  Mean reward : {mean_r:.4f}")
    print(f"  Std  reward : {std_r:.4f}")
    print(f"  Est. Sharpe : {sharpe:.4f}")


if __name__ == "__main__":
    main()
