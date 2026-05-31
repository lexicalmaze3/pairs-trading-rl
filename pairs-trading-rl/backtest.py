import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from stable_baselines3 import PPO
from env import PairsTradingEnv, COINT_WINDOW

MODEL_PATH   = "models/pairs_ppo_GLD_RTX.zip"
OOS_START    = "2025-01-01"
OOS_END      = "2026-05-26"
EQUITY_PNG   = "backtest_equity.png"
TRADES_CSV   = "backtest_trades.csv"


def run_backtest():
    # Build OOS env — episode spans all data after the lookback window
    env = PairsTradingEnv(start_date=OOS_START, end_date=OOS_END)
    n_steps = env._n - COINT_WINDOW
    env._episode_length = n_steps

    model = PPO.load(MODEL_PATH, env=env)

    obs, _ = env.reset(options={"episode_start": COINT_WINDOW})

    daily_pnl     = []
    trades        = []
    open_trade    = None   # {"entry_date", "direction", "entry_spread"}
    prev_spread   = None
    prev_position = 0

    step = -1
    for step in range(n_steps):
        action, _ = model.predict(obs, deterministic=True)
        obs, _, terminated, _, info = env.step(int(action))

        # Mark-to-market PnL of the position carried into this day, in spread
        # units — reconstructed from spread moves, NOT the RL `reward`, so the
        # equity curve and Sharpe reflect realized trading PnL and aren't
        # contaminated by reward shaping (holding cost, exit bonus, coint
        # penalty). Mirrors walk_forward.run_oos.
        spread = info["spread"]
        if prev_spread is not None:
            daily_pnl.append(prev_position * (spread - prev_spread))
        prev_spread   = spread
        prev_position = env.position

        date = env.dates[COINT_WINDOW + step]

        # Log on any position change — comparing against the open trade's
        # direction also catches direct long↔short flips.
        cur_dir = 0 if open_trade is None else (1 if open_trade["direction"] == "long" else -1)
        if env.position != cur_dir:
            if open_trade is not None:
                sign = 1 if open_trade["direction"] == "long" else -1
                pnl  = (spread - open_trade["entry_spread"]) * sign
                trades.append({
                    "entry_date": open_trade["entry_date"],
                    "exit_date":  date,
                    "direction":  open_trade["direction"],
                    "pnl":        round(pnl, 4),
                })
                open_trade = None
            if env.position != 0:
                open_trade = {
                    "entry_date":   date,
                    "direction":    "long" if env.position == 1 else "short",
                    "entry_spread": env.entry_spread,
                }

        if terminated:
            break

    # Close any trade still open at end of period
    if open_trade is not None:
        last_idx    = min(COINT_WINDOW + step, env._n - 1)
        exit_spread = env._spread[last_idx]
        sign = 1 if open_trade["direction"] == "long" else -1
        pnl  = (exit_spread - open_trade["entry_spread"]) * sign
        trades.append({
            "entry_date": open_trade["entry_date"],
            "exit_date":  env.dates[last_idx],
            "direction":  open_trade["direction"],
            "pnl":        round(pnl, 4),
        })

    # equity[i] = cumulative realized PnL at dates[i]; leading 0.0 = flat start.
    equity = np.cumsum([0.0] + daily_pnl)
    dates  = env.dates[COINT_WINDOW: COINT_WINDOW + len(equity)]
    return equity, daily_pnl, trades, dates


def compute_stats(trades, daily_pnl):
    df = pd.DataFrame(trades)

    total_trades = len(df)
    win_rate     = (df["pnl"] > 0).mean() if total_trades else 0.0

    arr = np.array(daily_pnl, dtype=float)
    if arr.size == 0:
        return total_trades, win_rate, 0.0, 0.0
    sharpe = (arr.mean() / arr.std() * np.sqrt(252)) if arr.std() > 0 else 0.0

    # Max drawdown from equity curve
    equity = np.cumsum(arr)
    peak   = np.maximum.accumulate(equity)
    dd     = equity - peak
    max_dd = float(dd.min())

    return total_trades, win_rate, sharpe, max_dd


def plot_equity(equity, dates):
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(dates[:len(equity)], equity, linewidth=1.5, color="#2196F3")
    ax.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax.fill_between(dates[:len(equity)], equity, 0,
                    where=[e >= 0 for e in equity], alpha=0.15, color="#4CAF50")
    ax.fill_between(dates[:len(equity)], equity, 0,
                    where=[e < 0 for e in equity],  alpha=0.15, color="#F44336")
    ax.set_title("GLD/RTX Pairs Trading — Out-of-Sample Equity Curve (2025–2026)", fontsize=13)
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative P&L (spread units)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(EQUITY_PNG, dpi=150)
    plt.close(fig)


def main():
    print(f"Loading model: {MODEL_PATH}")
    print(f"OOS window:    {OOS_START}  →  {OOS_END}\n")

    equity, daily_pnl, trades, dates = run_backtest()

    # Save trade log
    trades_df = pd.DataFrame(trades)
    trades_df.to_csv(TRADES_CSV, index=False)

    # Plot (equity and dates are already aligned, leading 0.0 = flat start)
    plot_equity(equity, dates)
    print(f"Equity curve saved → {EQUITY_PNG}")

    # Stats
    total_trades, win_rate, sharpe, max_dd = compute_stats(trades, daily_pnl)

    print("\n── Backtest Summary ─────────────────────────")
    print(f"  Total trades  : {total_trades}")
    print(f"  Win rate      : {win_rate:.1%}")
    print(f"  Sharpe ratio  : {sharpe:.4f}")
    print(f"  Max drawdown  : {max_dd:.4f}")
    print("─────────────────────────────────────────────")


if __name__ == "__main__":
    main()
