import argparse
import itertools
import sys
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint

warnings.filterwarnings("ignore")

# Print UTF-8 so decorative characters don't crash on Windows when redirected.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

WATCHLIST = [
    "SPY", "QQQ", "GLD", "SLV", "XOM", "CVX", "RTX", "LMT", "NOC",
    "AAPL", "MSFT", "AMZN", "XLE", "XLK", "XLF", "GDX",
]
PVALUE_THRESHOLD = 0.05


def download_prices(tickers: list[str], period: str = "3y",
                    start: str | None = None, end: str | None = None) -> pd.DataFrame:
    if start or end:
        raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False)
    else:
        raw = yf.download(tickers, period=period, auto_adjust=True, progress=False)
    prices = raw["Close"].dropna()
    if prices.empty:
        raise SystemExit("No price data downloaded — check tickers, dates, and network/yfinance.")
    print(f"Downloaded {len(prices)} trading days  ({prices.index[0].date()} → {prices.index[-1].date()})")
    print(f"Tickers: {list(prices.columns)}\n")
    return prices


def calc_half_life(spread: pd.Series) -> float:
    delta = spread.diff().dropna()
    lag = spread.shift(1).dropna()
    delta, lag = delta.align(lag, join="inner")
    model = sm.OLS(delta, sm.add_constant(lag)).fit()
    b = model.params.iloc[1]
    if b >= 0:
        return float("nan")
    return -np.log(2) / b


def test_pair(t1: str, t2: str, s1: pd.Series, s2: pd.Series) -> dict | None:
    _, pvalue, _ = coint(s1, s2)
    if pvalue >= PVALUE_THRESHOLD:
        return None

    # Hedge ratio via OLS: s1 = alpha + beta * s2
    model = sm.OLS(s1, sm.add_constant(s2)).fit()
    beta = model.params.iloc[1]

    spread = s1 - beta * s2
    half_life = calc_half_life(spread)
    std = spread.std()
    zscore = float((spread.iloc[-1] - spread.mean()) / std) if std > 0 else 0.0

    return {
        "pair":           f"{t1}/{t2}",
        "pvalue":         round(pvalue, 4),
        "hedge_ratio":    round(beta, 4),
        "half_life_days": round(half_life, 1) if not np.isnan(half_life) else "N/A",
        "zscore":         round(zscore, 3),
    }


def print_table(rows: list[dict]) -> None:
    if not rows:
        print("No cointegrated pairs found at p < 0.05.")
        return

    col_widths = {
        "pair":           12,
        "pvalue":          8,
        "hedge_ratio":    12,
        "half_life_days": 16,
        "zscore":          8,
    }
    headers = {
        "pair":           "Pair",
        "pvalue":         "P-Value",
        "hedge_ratio":    "Hedge Ratio",
        "half_life_days": "Half-Life(days)",
        "zscore":         "Z-Score",
    }

    header_line = "  ".join(f"{headers[k]:<{v}}" for k, v in col_widths.items())
    sep = "  ".join("-" * v for v in col_widths.values())
    print(header_line)
    print(sep)
    for row in rows:
        line = "  ".join(f"{str(row[k]):<{v}}" for k, v in col_widths.items())
        print(line)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=None, help="Start date YYYY-MM-DD")
    parser.add_argument("--end",   default=None, help="End date YYYY-MM-DD")
    args = parser.parse_args()

    prices = download_prices(WATCHLIST, start=args.start, end=args.end)

    pairs = list(itertools.combinations(WATCHLIST, 2))
    print(f"Testing {len(pairs)} pairs for cointegration (p < {PVALUE_THRESHOLD})...\n")

    results = []
    for t1, t2 in pairs:
        result = test_pair(t1, t2, prices[t1], prices[t2])
        if result:
            results.append(result)

    results.sort(key=lambda r: r["pvalue"])

    print(f"Found {len(results)} cointegrated pair(s):\n")
    print_table(results)

    out_path = "pairs_report.csv"
    pd.DataFrame(results).to_csv(out_path, index=False)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
