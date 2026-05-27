import os
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy
from env import PairsTradingEnv

MODEL_DIR  = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "pairs_ppo_GLD_RTX")

os.makedirs(MODEL_DIR, exist_ok=True)

env = PairsTradingEnv()

model = PPO(
    "MlpPolicy",
    env,
    n_steps=2048,
    batch_size=64,
    ent_coef=0.02,
    verbose=1,
)

model.learn(total_timesteps=200_000)
model.save(MODEL_PATH)
print(f"\nModel saved to {MODEL_PATH}.zip")

eval_env = PairsTradingEnv()
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
