import argparse
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from stable_baselines3 import PPO
from env import PairsTradingEnv, COST_BPS
from evaluate import run_episode

# Print UTF-8 so decorative characters don't crash on Windows when redirected.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

MODEL_PATH   = "models/pairs_ppo_GLD_RTX.zip"
OOS_START    = "2025-01-01"
OOS_END      = "2026-05-26"
EQUITY_PNG   = "backtest_equity.png"
TRADES_CSV   = "backtest_trades.csv"


def run_backtest(model_path, ticker1, ticker2, start, end, cost_bps=COST_BPS):
    env   = PairsTradingEnv(start_date=start, end_date=end,
                            ticker1=ticker1, ticker2=ticker2, cost_bps=cost_bps)
    model = PPO.load(model_path, env=env)

    steps, trades = run_episode(model, env)
    daily_pnl = [s["pnl"] for s in steps]
    dates     = [s["date"] for s in steps]
    equity    = np.cumsum(daily_pnl)  # cumulative net P&L, in spread units
    return equity, daily_pnl, trades, dates


def compute_stats(trades, daily_pnl):
    arr = np.asarray(daily_pnl, dtype=float)

    total_trades = len(trades)
    win_rate = (np.mean([t["pnl"] > 0 for t in trades])
                if total_trades else 0.0)

    sharpe = (arr.mean() / arr.std() * np.sqrt(252)) if arr.std() > 0 else 0.0
    total_pnl = float(arr.sum())

    equity = np.cumsum(arr)
    peak   = np.maximum.accumulate(equity) if len(equity) else np.array([0.0])
    max_dd = float((equity - peak).min()) if len(equity) else 0.0

    return total_trades, win_rate, sharpe, max_dd, total_pnl


def plot_equity(equity, dates, ticker1, ticker2):
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(dates, equity, linewidth=1.5, color="#2196F3")
    ax.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax.fill_between(dates, equity, 0, where=equity >= 0, alpha=0.15, color="#4CAF50")
    ax.fill_between(dates, equity, 0, where=equity < 0,  alpha=0.15, color="#F44336")
    ax.set_title(f"{ticker1}/{ticker2} Pairs Trading — Out-of-Sample Equity Curve",
                 fontsize=13)
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative P&L (spread units, net of costs)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(EQUITY_PNG, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Out-of-sample backtest of a trained pairs model.")
    parser.add_argument("--model",   default=MODEL_PATH)
    parser.add_argument("--ticker1", default="GLD")
    parser.add_argument("--ticker2", default="RTX")
    parser.add_argument("--start",   default=OOS_START)
    parser.add_argument("--end",     default=OOS_END)
    parser.add_argument("--cost-bps", default=COST_BPS, type=float,
                        help="Per-side transaction cost as a fraction of notional")
    args = parser.parse_args()

    print(f"Loading model: {args.model}")
    print(f"OOS window:    {args.start}  →  {args.end}\n")

    equity, daily_pnl, trades, dates = run_backtest(
        args.model, args.ticker1, args.ticker2, args.start, args.end, args.cost_bps)

    pd.DataFrame(trades).to_csv(TRADES_CSV, index=False)
    plot_equity(np.asarray(equity), dates, args.ticker1, args.ticker2)
    print(f"Equity curve saved → {EQUITY_PNG}")
    print(f"Trade log saved    → {TRADES_CSV}")

    total_trades, win_rate, sharpe, max_dd, total_pnl = compute_stats(trades, daily_pnl)

    print("\n── Backtest Summary (realized P&L, net of costs) ──")
    print(f"  Total trades   : {total_trades}")
    print(f"  Win rate       : {win_rate:.1%}")
    print(f"  Total P&L      : {total_pnl:.4f}  (spread units)")
    print(f"  Sharpe (ann.)  : {sharpe:.4f}")
    print(f"  Max drawdown   : {max_dd:.4f}")
    print("───────────────────────────────────────────────────")
    if total_trades < 30:
        print("  NOTE: very few trades — Sharpe/win-rate are not statistically reliable.")


if __name__ == "__main__":
    main()
