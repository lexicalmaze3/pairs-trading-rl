"""
Offline unit tests (no network) for the P&L accounting that all performance
reporting depends on. Run with:  pytest -q   (from the project directory)
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env import PairsTradingEnv, COINT_WINDOW  # noqa: E402
from evaluate import run_episode  # noqa: E402


def make_env(spread_p1, episode_length, cost_bps=0.0, hedge=2.2):
    """Build an env from a chosen ticker1 path with ticker2 held constant so the
    spread equals (p1 - hedge*const) and notional is easy to reason about."""
    p1 = np.asarray(spread_p1, dtype=float)
    p2 = np.full_like(p1, 10.0)
    dates = pd.date_range("2020-01-01", periods=len(p1), freq="D")
    return PairsTradingEnv(
        episode_length=episode_length,
        hedge_ratio=hedge,
        cost_bps=cost_bps,
        preloaded={"p1": p1, "p2": p2, "dates": dates},
    )


def test_pnl_equals_trade_gross_no_cost():
    # Long one round trip: enter at p1=11, exit at p1=10  -> spread P&L = -1.
    # Pad with constant tail so there is enough data for the look-back window.
    p1 = [10, 11, 13, 12] + [10.0] * 60
    env = make_env(p1, episode_length=4, cost_bps=0.0)
    env.reset(options={"episode_start": 1})

    actions = [1, 1, 1, 0]  # open long, hold, hold, close
    pnls = []
    for a in actions:
        _, _, terminated, _, info = env.step(a)
        pnls.append(info["pnl"])

    # entry spread 11, exit spread 10 -> gross = -1, no costs
    assert np.isclose(sum(pnls), -1.0)
    assert terminated


def test_pnl_includes_costs():
    p1 = [10, 11, 13, 12] + [10.0] * 60
    cost = 0.001
    env = make_env(p1, episode_length=4, cost_bps=cost, hedge=2.2)
    env.reset(options={"episode_start": 1})

    actions = [1, 1, 1, 0]
    pnls = []
    for a in actions:
        _, _, _, _, info = env.step(a)
        pnls.append(info["pnl"])

    # notional at entry (idx1) = p1+|hedge|*p2 = 11 + 2.2*10 = 33; exit (idx4)=10+22=32
    entry_cost = cost * 33.0
    exit_cost = cost * 32.0
    expected = -1.0 - entry_cost - exit_cost
    assert np.isclose(sum(pnls), expected)


def test_reward_is_unchanged_shaped_signal():
    # Reward must still carry the +MEAN_REVERT_BONUS shaping, independent of pnl.
    from env import MEAN_REVERT_BONUS
    # constant spread -> z-score 0 (in the [-0.5, 0.5] band) so the bonus fires.
    p1 = [22.0] * 64
    env = make_env(p1, episode_length=5, cost_bps=0.0)
    env.reset(options={"episode_start": 30})
    # open long then close near the mean: the closing reward includes the bonus.
    env.step(1)                          # open
    _, reward, _, _, _ = env.step(0)     # close near mean
    assert reward > MEAN_REVERT_BONUS - 0.1


class _ScriptedModel:
    """Minimal stand-in for a SB3 model: returns a preset action per call."""

    def __init__(self, actions):
        self._actions = list(actions)
        self._i = 0

    def predict(self, obs, deterministic=True):
        a = self._actions[min(self._i, len(self._actions) - 1)]
        self._i += 1
        return a, None


def test_run_episode_reconciles_and_handles_reversal():
    # Enough bars for the COINT_WINDOW warm-up plus a handful of trading steps.
    n = COINT_WINDOW + 8
    rng = np.random.default_rng(0)
    p1 = 100 + np.cumsum(rng.normal(0, 1, n))
    env = make_env(p1, episode_length=10, cost_bps=0.0005)

    # Force a long, hold, then a direct reversal to short, then flat.
    actions = [1, 1, 2, 2, 0, 0, 0, 0]
    model = _ScriptedModel(actions)

    steps, trades = run_episode(model, env)

    # Sum of per-bar realized P&L must equal sum of per-trade net P&L exactly,
    # even across a direct long->short reversal.
    assert len(trades) >= 2  # at least the long and the short were logged
    assert np.isclose(sum(s["pnl"] for s in steps),
                      sum(t["pnl"] for t in trades), atol=1e-6)


def test_nan_prices_rejected():
    p1 = [10.0, float("nan")] + [10.0] * (COINT_WINDOW + 5)
    try:
        make_env(p1, episode_length=5)
    except ValueError:
        return
    raise AssertionError("env should reject NaN price series")


if __name__ == "__main__":
    # Allow running without pytest:  python tests/test_pnl.py
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL  {t.__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
