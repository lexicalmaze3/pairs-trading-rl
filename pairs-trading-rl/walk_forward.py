"""
Walk-forward pairs trading evaluation.

Downloads all data ONCE, then slices numpy arrays per fold — no per-fold
network calls, no yfinance rate-limit hangs.

Timeline per fold:
  |<────── train 252d ──────>|<── oos 60d ──>|
                              roll 60d →
"""

import itertools
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint
from stable_baselines3 import PPO
from env import PairsTradingEnv, COINT_WINDOW

warnings.filterwarnings("ignore")

WATCHLIST = [
    "SPY", "QQQ", "GLD", "SLV", "XOM", "CVX", "RTX", "LMT", "NOC",
    "AAPL", "MSFT", "AMZN", "XLE", "XLK", "XLF", "GDX",
]
START_DATE    = "2022-01-01"
END_DATE      = "2026-05-26"
TRAIN_DAYS    = 252
OOS_DAYS      = 60
STEP_DAYS     = 60
TIMESTEPS     = 100_000
PVALUE_THRESH = 0.05


# ── Data ──────────────────────────────────────────────────────────────────────

def download_all() -> pd.DataFrame:
    raw = yf.download(WATCHLIST, start=START_DATE, end=END_DATE,
                      auto_adjust=True, progress=False)
    prices = raw["Close"].dropna(how="all")
    print(f"Master data: {len(prices)} days  "
          f"({prices.index[0].date()} → {prices.index[-1].date()})")
    print(f"Tickers loaded: {list(prices.columns)}\n")
    return prices


# ── Screening ─────────────────────────────────────────────────────────────────

def screen_window(prices: pd.DataFrame) -> list[dict]:
    results = []
    for t1, t2 in itertools.combinations(prices.columns, 2):
        s1 = prices[t1].dropna()
        s2 = prices[t2].dropna()
        common = s1.index.intersection(s2.index)
        s1, s2 = s1[common], s2[common]
        if len(s1) < 60:
            continue
        try:
            _, pval, _ = coint(s1, s2)
        except Exception:
            continue
        if pval >= PVALUE_THRESH:
            continue
        model = sm.OLS(s1, sm.add_constant(s2)).fit()
        beta  = float(model.params.iloc[1])
        results.append({"t1": t1, "t2": t2, "pvalue": pval, "hedge_ratio": beta})
    results.sort(key=lambda r: r["pvalue"])
    return results


# ── Env factory (no download) ─────────────────────────────────────────────────

def make_env(all_prices: pd.DataFrame,
             t1: str, t2: str, hedge: float,
             start_i: int, end_i: int,
             episode_length: int) -> PairsTradingEnv:
    """Slice pre-downloaded arrays and hand them directly to the env."""
    slice_df = all_prices.iloc[start_i:end_i]
    return PairsTradingEnv(
        episode_length=episode_length,
        ticker1=t1, ticker2=t2, hedge_ratio=hedge,
        preloaded={
            "p1":    slice_df[t1].to_numpy(),
            "p2":    slice_df[t2].to_numpy(),
            "dates": slice_df.index,
        },
    )


# ── OOS evaluation ────────────────────────────────────────────────────────────

def run_oos(model, env: PairsTradingEnv) -> tuple[list, list]:
    n_steps = env._n - COINT_WINDOW
    env._episode_length = n_steps
    obs, _ = env.reset(options={"episode_start": COINT_WINDOW})

    daily_pnl  = []
    trades     = []
    open_trade = None

    for step in range(n_steps):
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, terminated, _, info = env.step(int(action))
        daily_pnl.append(reward)

        date = env.dates[min(COINT_WINDOW + step, env._n - 1)]

        if open_trade is None and env.position != 0:
            open_trade = {
                "entry_date":   date,
                "direction":    "long" if env.position == 1 else "short",
                "entry_spread": env.entry_spread,
            }

        if open_trade is not None and env.position == 0:
            sign = 1 if open_trade["direction"] == "long" else -1
            pnl  = (info["spread"] - open_trade["entry_spread"]) * sign
            trades.append({**open_trade, "exit_date": date, "pnl": round(pnl, 4)})
            open_trade = None

        if terminated:
            break

    if open_trade is not None:
        last_idx = min(COINT_WINDOW + step, env._n - 1)
        sign     = 1 if open_trade["direction"] == "long" else -1
        pnl      = (env._spread[last_idx] - open_trade["entry_spread"]) * sign
        trades.append({
            **open_trade,
            "exit_date": env.dates[last_idx],
            "pnl":       round(float(pnl), 4),
        })

    return daily_pnl, trades


def oos_stats(daily_pnl: list, trades: list) -> tuple[float, int, float]:
    arr    = np.array(daily_pnl)
    sharpe = float(arr.mean() / arr.std() * np.sqrt(252)) if arr.std() > 0 else 0.0
    n      = len(trades)
    wr     = sum(1 for t in trades if t["pnl"] > 0) / n if n > 0 else float("nan")
    return sharpe, n, wr


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    all_prices = download_all()
    all_dates  = all_prices.index
    total      = len(all_dates)

    fold_starts = list(range(0, total - TRAIN_DAYS - OOS_DAYS, STEP_DAYS))
    print(f"Running {len(fold_starts)} folds  "
          f"(train={TRAIN_DAYS}d, oos={OOS_DAYS}d, step={STEP_DAYS}d)\n")

    records    = []
    all_trades = []

    for fold_i, start_i in enumerate(fold_starts):
        end_train_i = start_i + TRAIN_DAYS
        end_oos_i   = start_i + TRAIN_DAYS + OOS_DAYS

        t_start = all_dates[start_i]
        t_end   = all_dates[end_train_i - 1]
        o_start = all_dates[end_train_i]
        o_end   = all_dates[end_oos_i - 1]

        print(f"── Fold {fold_i+1:02d}  "
              f"train {t_start.date()} → {t_end.date()}  "
              f"oos {o_start.date()} → {o_end.date()}")

        # Screen training window (pure in-memory pandas slice)
        train_slice = all_prices.iloc[start_i:end_train_i]
        pairs = screen_window(train_slice)

        if not pairs:
            print("         no cointegrated pairs — skipping\n")
            records.append({
                "fold": fold_i + 1,
                "train_start": str(t_start.date()), "train_end": str(t_end.date()),
                "oos_start":   str(o_start.date()), "oos_end":   str(o_end.date()),
                "pair": "none", "pvalue": None,
                "oos_sharpe": None, "oos_trades": 0, "oos_winrate": None,
            })
            continue

        best   = pairs[0]
        t1, t2 = best["t1"], best["t2"]
        hedge  = best["hedge_ratio"]
        print(f"         best pair {t1}/{t2}  p={best['pvalue']:.4f}  hedge={hedge:.4f}")

        # Train — episode spans full training window minus lookback
        train_env = make_env(all_prices, t1, t2, hedge,
                             start_i, end_train_i,
                             episode_length=TRAIN_DAYS - COINT_WINDOW)
        model = PPO("MlpPolicy", train_env,
                    n_steps=2048, batch_size=64, ent_coef=0.02, verbose=0)
        model.learn(total_timesteps=TIMESTEPS)
        print(f"         trained {TIMESTEPS:,} steps")

        # OOS eval — prepend COINT_WINDOW days of lookback before OOS window
        lookback_i = end_train_i - COINT_WINDOW
        oos_env = make_env(all_prices, t1, t2, hedge,
                           lookback_i, end_oos_i,
                           episode_length=OOS_DAYS)
        daily_pnl, trades = run_oos(model, oos_env)
        sharpe, n_trades, wr = oos_stats(daily_pnl, trades)

        for tr in trades:
            all_trades.append({**tr, "fold": fold_i + 1, "pair": f"{t1}/{t2}"})

        wr_pct = f"{wr:.0%}" if not np.isnan(wr) else "n/a"
        print(f"         oos → sharpe={sharpe:.3f}  trades={n_trades}  winrate={wr_pct}\n")

        records.append({
            "fold": fold_i + 1,
            "train_start": str(t_start.date()), "train_end": str(t_end.date()),
            "oos_start":   str(o_start.date()), "oos_end":   str(o_end.date()),
            "pair":        f"{t1}/{t2}",
            "pvalue":      round(best["pvalue"], 4),
            "oos_sharpe":  round(sharpe, 4),
            "oos_trades":  n_trades,
            "oos_winrate": round(wr, 4) if not np.isnan(wr) else None,
        })

    # Save
    results_df = pd.DataFrame(records)
    results_df.to_csv("walk_forward_results.csv", index=False)
    if all_trades:
        pd.DataFrame(all_trades).to_csv("walk_forward_trades.csv", index=False)

    # Summary table
    SEP = "═" * 82
    print(f"\n{SEP}")
    print("  Walk-Forward Summary")
    print(SEP)
    hdr = (f"{'Fold':>4}  {'Pair':<12}  {'OOS Start':<11}  "
           f"{'OOS End':<11}  {'Sharpe':>8}  {'Trades':>6}  {'WinRate':>8}")
    print(hdr)
    print("─" * 82)
    for r in records:
        s  = f"{r['oos_sharpe']:>8.3f}" if r["oos_sharpe"] is not None else "       —"
        wr = f"{r['oos_winrate']:>7.0%}" if r["oos_winrate"] is not None else "       —"
        print(f"{r['fold']:>4}  {r['pair']:<12}  {r['oos_start']:<11}  "
              f"{r['oos_end']:<11}  {s}  {r['oos_trades']:>6}  {wr}")
    print(SEP)

    valid = results_df.dropna(subset=["oos_sharpe"])
    if not valid.empty:
        print(f"\n  Avg OOS Sharpe  : {valid['oos_sharpe'].mean():.3f}")
        print(f"  Avg Win Rate    : {valid['oos_winrate'].mean():.1%}")
        print(f"  Total OOS Trades: {int(results_df['oos_trades'].sum())}")

    print(f"\n  Saved: walk_forward_results.csv")
    if all_trades:
        print(f"  Saved: walk_forward_trades.csv  ({len(all_trades)} trades)")


if __name__ == "__main__":
    main()
