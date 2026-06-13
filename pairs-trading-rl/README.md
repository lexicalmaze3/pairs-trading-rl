# Pairs Trading RL

A reinforcement-learning research framework for **statistical-arbitrage (pairs) trading** of U.S. equities and ETFs. It screens a universe of tickers for cointegrated pairs, trains a PPO agent to trade the spread, and evaluates the agent with a rigorous, look-ahead-free **walk-forward** procedure.

> ⚠️ **Important — read the [Disclaimer](#disclaimer) before using this software.** This is an educational/research tool, **not** investment advice and **not** a turnkey profitable trading system. Backtested results do not predict live performance.

## What it does

1. **Screen** a watchlist for cointegrated pairs (Engle–Granger test) and estimate each pair's hedge ratio.
2. **Train** a PPO agent (Stable-Baselines3) to go long/short/flat on the spread, observing the rolling z-score, current position, time-in-trade, and a rolling cointegration p-value.
3. **Evaluate** out-of-sample, rolling the train/test windows forward across history so the agent is always tested on data it never trained on.

## Files

| File | Purpose |
|------|---------|
| `screener.py` | Tests all pairs in the watchlist for cointegration, ranks by p-value, reports hedge ratio, half-life, and current z-score. |
| `env.py` | Gymnasium environment. Computes the spread and rolling z-score, shapes a learning **reward**, and reports realized **P&L** (`info["pnl"]`) net of transaction costs. |
| `evaluate.py` | Single shared, deterministic evaluation loop used by both the backtest and walk-forward (so they always measure the same thing). |
| `train.py` | Screens/selects a pair and trains a PPO agent on a fixed window. |
| `backtest.py` | Loads a saved model and runs an out-of-sample backtest, producing an equity curve and trade log. |
| `walk_forward.py` | Full pipeline: per fold, re-screen → retrain → evaluate on the next out-of-sample window. |

## Reward vs. P&L (read this)

The environment returns two different quantities, and **they are not the same**:

- **`reward`** — a *shaped* RL training signal. It includes a bonus for closing the spread near its mean and penalties for holding and for weak cointegration. It is intentionally not dollar-accurate; it only exists to guide learning.
- **`info["pnl"]`** — the **realized, mark-to-market profit and loss** for each bar, in spread units, **net of transaction costs**. This is the only quantity used to compute reported performance (Sharpe, win rate, equity curve, drawdown).

Earlier versions of this project computed performance from the shaped reward, which produced wildly inflated and misleading Sharpe numbers. All performance reporting now uses `info["pnl"]`.

### Costs and units

- P&L is expressed in **spread units** (price of ticker1 minus `hedge_ratio` × price of ticker2), not dollars of a sized portfolio.
- Transaction costs are modeled as `COST_BPS` per side (default **5 bps** of traded notional, configurable in `env.py` / `--cost-bps`). A round trip costs roughly twice that. Borrow/financing costs and market impact beyond this flat estimate are **not** modeled.

## Installation

```bash
pip install -r requirements.txt
```

Requires Python 3.10+ and a working internet connection (price data is pulled live via `yfinance`).

## Usage

```bash
# 1. Find cointegrated pairs in the watchlist
python screener.py

# 2. Train an agent on a pair
python train.py --ticker1 GLD --ticker2 RTX --timesteps 200000 --seed 42

# 3. Out-of-sample backtest of a saved model
python backtest.py --ticker1 GLD --ticker2 RTX --start 2025-01-01 --end 2026-05-26

# 4. Full walk-forward evaluation across all folds
python walk_forward.py
```

### Tests

Offline unit tests validate the P&L accounting (no network needed):

```bash
python tests/test_pnl.py     # or: pytest -q
```

### Outputs

- `pairs_report.csv` — screener results.
- `backtest_trades.csv`, `backtest_equity.png` — backtest trade log and equity curve.
- `walk_forward_results.csv` (per-fold summary) and `walk_forward_trades.csv` (every trade).

All performance figures in these files are realized P&L, net of modeled costs.

## Reproducing results

Because the system pulls live market data and retrains agents, results depend on the data available at run time and on RNG seeds. **Run `python walk_forward.py` to generate your own results table** rather than relying on figures quoted in documentation. A pre-trained demo model (`models/pairs_ppo_GLD_RTX.zip`) is included so `backtest.py` runs out of the box; for any serious use, retrain.

When interpreting results, note that most folds produce **very few trades** (often one per 60-day window). Sharpe ratios and win rates computed from a handful of trades are **not statistically reliable** — treat them as illustrative, not as evidence of edge.

## Limitations & risks

- **Multiple-testing / data-mining bias.** The screener tests dozens of pairs and keeps the most significant; with no correction for multiple comparisons, some "cointegrated" pairs are false positives.
- **Regime dependence.** Cointegration is not stable; a pair that passes screening can break down inside the test window.
- **Tiny sample of trades.** Headline statistics rest on few trades and have wide error bars.
- **Spread units, not dollars.** P&L is not a sized, capitalized portfolio return; there is no position sizing, leverage, or risk budgeting.
- **Cost model is simplistic.** A flat per-side bps cost ignores slippage, market impact, short-borrow fees, and financing.
- **Survivorship / selection.** The watchlist is hand-picked from currently listed liquid names.
- **Execution assumptions.** Trades are assumed to fill at the daily close; intraday execution risk is not modeled.

## License

No license is included. Choose and add a license (or a commercial EULA) appropriate to how you intend to distribute this software before publishing it.

## Disclaimer

This software is provided for **educational and research purposes only**. It is **not** financial, investment, legal, or tax advice, and **nothing here is a recommendation to buy or sell any security**. Trading involves substantial risk of loss. Past and backtested performance is not indicative of future results. The authors and contributors make **no warranty** of any kind and accept **no liability** for any losses arising from use of this software. Use entirely at your own risk, and consult a licensed professional before making investment decisions.
