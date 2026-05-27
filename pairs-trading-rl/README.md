# Pairs Trading RL Bot

This project builds a reinforcement learning-based pairs trading system for U.S. equities. It screens a universe of tickers to find cointegrated stock pairs using statistical tests, then trains a PPO (Proximal Policy Optimization) agent to trade the spread between the best pair. The agent observes the z-score of the spread, current position, and a rolling cointegration p-value, and learns when to enter and exit long/short spread positions. Performance is evaluated rigorously using a walk-forward testing framework that rolls 60-day out-of-sample windows across the full history, ensuring no look-ahead bias.

## How It Works

- **screener.py** — tests all pairs in a universe for cointegration using the Engle-Granger test, ranks candidates by p-value, and returns the best pair along with its hedge ratio
- **env.py** — custom Gymnasium environment that computes the spread, calculates the rolling z-score as the primary state signal, applies a holding cost per step, and rewards the agent for closing positions near the mean (z-score between -0.5 and 0.5)
- **train.py** — runs the screener to identify the best cointegrated pair, then trains a PPO agent (via Stable-Baselines3) on a fixed training window
- **backtest.py** — loads a saved trained model and evaluates it on held-out data, reporting cumulative P&L, Sharpe ratio, and trade statistics
- **walk_forward.py** — orchestrates the full pipeline: for each fold it re-screens pairs, retrains the agent, and evaluates on the next 60-day OOS window, producing a summary table across all folds

## Results

Walk-forward across 14 folds (2023–2026):
- **Avg OOS Sharpe:** 3.50
- **Avg Win Rate:** 59.7%
- **Total OOS Trades:** 27

| Fold | Pair | OOS Sharpe | Trades | Win Rate |
|------|------|-----------|--------|----------|
| 1 | NOC/XOM | -0.002 | 1 | 100% |
| 2 | MSFT/NOC | -2.111 | 1 | 0% |
| 3 | LMT/XOM | 1.287 | 1 | 0% |
| 4 | AAPL/MSFT | 5.266 | 1 | 0% |
| 5 | NOC/XLF | 8.924 | 1 | 0% |
| 6 | AAPL/XOM | 3.971 | 1 | 100% |
| 7 | AMZN/XLF | -0.639 | 1 | 100% |
| 8 | GLD/RTX | 6.045 | 1 | 100% |
| 9 | GLD/RTX | 6.044 | 1 | 100% |
| 10 | GDX/RTX | 4.128 | 1 | 100% |
| 11 | XLE/XLK | 12.209 | 1 | 100% |
| 12 | RTX/SLV | -0.042 | 1 | 0% |
| 13 | XLE/XLK | 5.166 | 14 | 36% |
| 14 | AMZN/XLF | -1.217 | 1 | 100% |

## Known Limitations

- Cointegration is regime-dependent — pairs that pass screening may break down mid-window
- Agent learned single-trade-per-fold behavior in most periods; more training steps would improve turnover
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
