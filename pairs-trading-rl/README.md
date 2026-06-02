# Pairs Trading RL Bot

This project builds a reinforcement learning-based pairs trading system for U.S. equities. It screens a universe of tickers to find cointegrated stock pairs using statistical tests, then trains a PPO (Proximal Policy Optimization) agent to trade the spread between the best pair. The agent observes the z-score of the spread, current position, and a rolling cointegration p-value, and learns when to enter and exit long/short spread positions. Performance is evaluated rigorously using a walk-forward testing framework that rolls 60-day out-of-sample windows across the full history, ensuring no look-ahead bias.

## How It Works

- **screener.py** — tests all pairs in a universe for cointegration using the Engle-Granger test, ranks candidates by p-value, and returns the best pair along with its hedge ratio
- **env.py** — custom Gymnasium environment that computes the spread, calculates the rolling z-score as the primary state signal, applies a holding cost per step, and rewards the agent for closing positions near the mean (z-score between -0.5 and 0.5)
- **train.py** — runs the screener to identify the best cointegrated pair, then trains a PPO agent (via Stable-Baselines3) on a fixed training window
- **backtest.py** — loads a saved trained model and evaluates it on held-out data, reporting cumulative P&L, Sharpe ratio, and trade statistics
- **walk_forward.py** — orchestrates the full pipeline: for each fold it re-screens pairs, retrains the agent, and evaluates on the next 60-day OOS window, producing a summary table across all folds

## Results

Walk-forward across 14 folds (Jan 2023 – May 2026). OOS Sharpe is measured on
**realized spread PnL**, not the shaped training reward:

- **Avg OOS Sharpe:** −0.41
- **Avg Win Rate:** 51.7%
- **Total OOS Trades:** 341
- 6 of 14 folds positive

| Fold | Pair | OOS Start | OOS End | Sharpe | Trades | Win Rate |
|------|------|-----------|---------|-------:|-------:|---------:|
| 1 | NOC/XOM | 2023-01-04 | 2023-03-30 | -1.000 | 12 | 58% |
| 2 | MSFT/NOC | 2023-03-31 | 2023-06-27 | -2.211 | 1 | 0% |
| 3 | LMT/XOM | 2023-06-28 | 2023-09-21 | 0.809 | 19 | 74% |
| 4 | AAPL/MSFT | 2023-09-22 | 2023-12-15 | 0.472 | 20 | 65% |
| 5 | NOC/XLF | 2023-12-18 | 2024-03-14 | 3.192 | 36 | 69% |
| 6 | AAPL/XOM | 2024-03-15 | 2024-06-10 | 0.843 | 23 | 57% |
| 7 | AMZN/XLF | 2024-06-11 | 2024-09-05 | -0.906 | 12 | 58% |
| 8 | GLD/RTX | 2024-09-06 | 2024-11-29 | 1.097 | 19 | 53% |
| 9 | GLD/RTX | 2024-12-02 | 2025-02-28 | -0.080 | 46 | 48% |
| 10 | GDX/RTX | 2025-03-03 | 2025-05-27 | 1.465 | 16 | 69% |
| 11 | XLE/XLK | 2025-05-28 | 2025-08-21 | -0.388 | 57 | 49% |
| 12 | RTX/SLV | 2025-08-22 | 2025-11-14 | -1.461 | 17 | 35% |
| 13 | XLE/XLK | 2025-11-17 | 2026-02-12 | -4.717 | 37 | 43% |
| 14 | AMZN/XLF | 2026-02-13 | 2026-05-11 | -2.822 | 26 | 46% |

> **Note on a prior +3.50 claim.** An earlier version of this README reported an
> avg Sharpe of +3.50 over 27 trades. That figure was an artifact: Sharpe was
> computed on the *shaped RL reward* (which includes a +2.0 mean-reversion exit
> bonus and holding costs) rather than realized PnL, and the agent did roughly
> one trade per fold, so the statistic was dominated by a few lucky daily moves
> (e.g. fold 11 read +12.2; on realized PnL it is −0.39). Measured correctly on
> realized spread PnL with proper trade accounting, the strategy shows **no
> positive out-of-sample edge**.

## Known Limitations

- **No demonstrated OOS edge** — avg realized Sharpe is slightly negative, and this is *gross* of transaction costs (the environment models none; with realistic costs on 341 trades, net performance would be worse)
- Sharpe is highly dispersed across folds (−4.7 to +3.2) — the outcome depends heavily on which single pair the screener selects each fold
- Cointegration is regime-dependent — pairs that pass screening may break down mid-window (see the sharply negative late folds)
- Results are in raw spread units, not dollar P&L

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python screener.py
python train.py --ticker1 GLD --ticker2 RTX
python backtest.py
python walk_forward.py
```
