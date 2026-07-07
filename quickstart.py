"""Zero-friction quickstart for Pairs Trading RL.

No arguments, no config, no API keys, no downloads. A bundled *synthetic*
cointegrated pair (sample_data/pair_sample.csv) is traded by the pre-trained
PPO agent that ships in models/. Run it from the repository root:

    python quickstart.py

Expected output (a few seconds):
  - quickstart_output.png : the agent's out-of-sample cumulative P&L (in spread
    units, net of costs) on the synthetic pair.
  - A 3-line summary printed to the console, e.g.:

      Synthetic pair      : 390 bars, cointegration p-value 0.005 (clearly cointegrated)
      Trades taken        : 12  (win rate 58%)
      Total P&L           : +6.83 spread units, net of costs

The data here is a deliberately synthetic, mean-reverting pair used only to
show the full screen->trade->evaluate loop running end to end offline. No
headline Sharpe is reported: on a handful of trades it is not statistically
meaningful (see the README's "Reproducing results" section). For real numbers,
run walk_forward.py on live data.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import matplotlib

matplotlib.use("Agg")  # render straight to a file; no display needed

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint
from stable_baselines3 import PPO

from env import PairsTradingEnv, HEDGE_RATIO
from evaluate import run_episode

SAMPLE_CSV = ROOT / "sample_data" / "pair_sample.csv"
MODEL_PATH = ROOT / "models" / "pairs_ppo_GLD_RTX.zip"
OUTPUT_PNG = ROOT / "quickstart_output.png"


def main() -> None:
    df = pd.read_csv(SAMPLE_CSV, parse_dates=["date"])
    p1 = df["syn_a"].to_numpy(dtype=np.float64)
    p2 = df["syn_b"].to_numpy(dtype=np.float64)
    dates = pd.DatetimeIndex(df["date"])

    coint_p = float(coint(p1, p2)[1])

    # Drive the env from bundled arrays instead of yfinance (the `preloaded`
    # path), then let the shipped PPO agent trade the spread deterministically.
    env = PairsTradingEnv(
        ticker1="SYN-A",
        ticker2="SYN-B",
        hedge_ratio=HEDGE_RATIO,
        preloaded={"p1": p1, "p2": p2, "dates": dates},
    )
    model = PPO.load(str(MODEL_PATH))  # env passed to run_episode directly below
    steps, trades = run_episode(model, env)

    daily_pnl = np.array([s["pnl"] for s in steps], dtype=float)
    step_dates = [s["date"] for s in steps]
    equity = np.cumsum(daily_pnl)  # cumulative net P&L, in spread units

    # --- Plot: out-of-sample cumulative P&L ---------------------------------
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(step_dates, equity, lw=1.6, color="#2196F3")
    ax.axhline(0, color="gray", lw=0.8, ls="--")
    ax.fill_between(step_dates, equity, 0, where=equity >= 0, alpha=0.15, color="#4CAF50")
    ax.fill_between(step_dates, equity, 0, where=equity < 0, alpha=0.15, color="#F44336")
    ax.set_title("PPO agent on a synthetic cointegrated pair — cumulative P&L (net of costs)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative P&L (spread units)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_PNG, dpi=150)
    plt.close(fig)

    # --- 3-line summary (no headline Sharpe — see module docstring) ---------
    n_trades = len(trades)
    win_rate = np.mean([t["pnl"] > 0 for t in trades]) if n_trades else 0.0
    total_pnl = float(daily_pnl.sum())

    print(f"Synthetic pair      : {len(steps)} bars, cointegration p-value {coint_p:.3f} (clearly cointegrated)")
    print(f"Trades taken        : {n_trades}  (win rate {win_rate:.0%})")
    print(f"Total P&L           : {total_pnl:+.2f} spread units, net of costs")
    print(f"\nSaved plot -> {OUTPUT_PNG.name}")


if __name__ == "__main__":
    main()
