import warnings
import numpy as np
import pandas as pd
import yfinance as yf
import gymnasium as gym
from gymnasium import spaces
from statsmodels.tsa.stattools import coint

warnings.filterwarnings("ignore")

HEDGE_RATIO      = 2.2304
EPISODE_LENGTH   = 252          # ~1 trading year
COINT_WINDOW     = 60           # days used for rolling cointegration
COINT_INTERVAL   = 20           # recalculate every N steps
HOLDING_COST     = 0.005        # reward shaping: per step while position is open
WEAK_COINT_PEN   = 0.01         # reward shaping: penalty when p-value > threshold
WEAK_COINT_THRESH = 0.1
MEAN_REVERT_BONUS = 2.0         # reward shaping: bonus for closing near the mean
COST_BPS         = 0.0005       # per-side transaction cost (fraction of notional)


class PairsTradingEnv(gym.Env):
    """
    Pairs trading environment for a single cointegrated pair.

    Spread = price(ticker1) - hedge_ratio * price(ticker2)

    Actions:
        0 = go flat  (close any open position)
        1 = long spread
        2 = short spread

    Observation (4 floats):
        [z-score, position (-1/0/1), steps_since_entry/episode_length, coint_p_value]

    Reward vs. P&L
    --------------
    The ``reward`` returned by :meth:`step` is a *shaped* learning signal
    (realized spread P&L plus a mean-reversion bonus, minus holding/weak-coint
    penalties). It is NOT a dollar-accurate return and must never be used to
    measure performance. For that, use ``info["pnl"]``: the realized
    mark-to-market P&L for the bar, in spread units, net of transaction costs.
    Backtests and walk-forward stats are built from ``info["pnl"]``.
    """

    metadata = {"render_modes": []}

    def __init__(self, render_mode=None,
                 start_date="2023-01-01", end_date="2025-01-01",
                 episode_length=None,
                 ticker1="GLD", ticker2="RTX", hedge_ratio=HEDGE_RATIO,
                 cost_bps=COST_BPS,
                 preloaded: dict | None = None):
        """
        Parameters
        ----------
        cost_bps : per-side transaction cost as a fraction of traded notional
                   (e.g. 0.0005 = 5 bps). Applied to ``info["pnl"]`` on every
                   position change; a round trip therefore costs ~2 * cost_bps.
        preloaded : optional dict with keys 'p1', 'p2', 'dates' (numpy arrays /
                    DatetimeIndex).  When supplied the env skips yfinance and uses
                    these arrays directly — useful in walk-forward loops where data
                    is already downloaded.
        """
        super().__init__()

        self._cost_bps = float(cost_bps)

        self.observation_space = spaces.Box(
            low  = np.array([-5.0, -1.0, 0.0, 0.0], dtype=np.float32),
            high = np.array([ 5.0,  1.0, 1.0, 1.0], dtype=np.float32),
            dtype=np.float32,
        )
        self.action_space = spaces.Discrete(3)

        self._ticker1      = ticker1
        self._ticker2      = ticker2
        self._hedge_ratio  = hedge_ratio
        if preloaded is not None:
            self._p1     = preloaded["p1"].astype(np.float64)
            self._p2     = preloaded["p2"].astype(np.float64)
            self.dates   = preloaded["dates"]
            self._spread = self._p1 - self._hedge_ratio * self._p2
            self._n      = len(self._spread)
        else:
            self._load_data(start_date, end_date)
        self._validate_prices()
        self._episode_length = episode_length if episode_length is not None else EPISODE_LENGTH

        # episode state — populated in reset()
        self.episode_start    = 0
        self.current_step     = 0
        self.position         = 0
        self.entry_spread     = 0.0
        self.steps_since_entry = 0
        self._coint_pvalue    = 0.0
        self._steps_since_coint = COINT_INTERVAL  # trigger calc on first reset

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _load_data(self, start_date, end_date):
        raw = yf.download(
            [self._ticker1, self._ticker2],
            start=start_date, end=end_date,
            auto_adjust=True, progress=False,
        )
        prices   = raw["Close"].dropna()
        self._p1     = prices[self._ticker1].to_numpy(dtype=np.float64)
        self._p2     = prices[self._ticker2].to_numpy(dtype=np.float64)
        self._spread = self._p1 - self._hedge_ratio * self._p2
        self._n      = len(self._spread)
        self.dates   = prices.index

    def _validate_prices(self):
        if not (np.all(np.isfinite(self._p1)) and np.all(np.isfinite(self._p2))):
            raise ValueError(
                f"{self._ticker1}/{self._ticker2}: price series contain NaN/inf. "
                "Both tickers need complete, overlapping history for the window."
            )
        if self._n < COINT_WINDOW + 2:
            raise ValueError(
                f"{self._ticker1}/{self._ticker2}: only {self._n} bars available; "
                f"need at least {COINT_WINDOW + 2}."
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _zscore_at(self, idx: int) -> float:
        lo  = max(0, idx - COINT_WINDOW + 1)
        win = self._spread[lo : idx + 1]
        if len(win) < 2:
            return 0.0
        std = win.std()
        return 0.0 if std == 0 else float((self._spread[idx] - win.mean()) / std)

    def _coint_pvalue_at(self, idx: int) -> float:
        lo = max(0, idx - COINT_WINDOW + 1)
        if (idx - lo) < 30:
            return 1.0  # too little data to assert cointegration -> treat as weak
        try:
            _, pval, _ = coint(self._p1[lo:idx+1], self._p2[lo:idx+1])
            return float(np.clip(pval, 0.0, 1.0))
        except Exception:
            return 1.0

    def _txn_cost(self, idx: int) -> float:
        """Cost (spread units) to trade one unit of the spread at bar ``idx``:
        one share of ticker1 plus |hedge_ratio| shares of ticker2."""
        notional = abs(self._p1[idx]) + abs(self._hedge_ratio) * abs(self._p2[idx])
        return self._cost_bps * notional

    def _maybe_refresh_coint(self):
        self._steps_since_coint += 1
        if self._steps_since_coint >= COINT_INTERVAL:
            idx = self.episode_start + self.current_step
            self._coint_pvalue      = self._coint_pvalue_at(idx)
            self._steps_since_coint = 0

    def _obs(self) -> np.ndarray:
        idx    = min(self.episode_start + self.current_step, self._n - 1)
        zscore = np.clip(self._zscore_at(idx), -5.0, 5.0)
        return np.array(
            [zscore,
             float(self.position),
             self.steps_since_entry / self._episode_length,
             self._coint_pvalue],
            dtype=np.float32,
        )

    # ------------------------------------------------------------------
    # Gymnasium API
    # ------------------------------------------------------------------

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        if options is not None and "episode_start" in options:
            self.episode_start = int(options["episode_start"])
        else:
            lo = COINT_WINDOW
            hi = self._n - self._episode_length - 1
            self.episode_start = int(self.np_random.integers(lo, max(lo, hi) + 1))
        self.current_step      = 0
        self.position          = 0
        self.entry_spread      = 0.0
        self.steps_since_entry = 0

        # Force immediate cointegration calculation
        self._coint_pvalue      = self._coint_pvalue_at(self.episode_start)
        self._steps_since_coint = 0

        return self._obs(), {}

    def step(self, action: int):
        assert self.action_space.contains(action), f"Invalid action {action}"

        idx            = self.episode_start + self.current_step
        current_spread = self._spread[idx]
        desired_pos    = {0: 0, 1: 1, 2: -1}[int(action)]

        reward = 0.0

        # --- Realized P&L (info["pnl"]): mark-to-market the position we held
        #     into this bar, then deduct transaction costs on any change. This
        #     is the dollar-accurate series used for performance reporting. ---
        prev_spread = self._spread[idx - 1] if self.current_step > 0 else current_spread
        pnl = self.position * (current_spread - prev_spread)

        # --- Close position if direction changes or going flat ---
        if self.position != 0 and desired_pos != self.position:
            reward += (current_spread - self.entry_spread) * self.position
            zscore_now = self._zscore_at(idx)
            if -0.5 <= zscore_now <= 0.5:
                reward += MEAN_REVERT_BONUS
            pnl -= self._txn_cost(idx) * abs(self.position)
            self.position       = 0
            self.steps_since_entry = 0

        # --- Open new position ---
        if desired_pos != 0 and self.position == 0:
            self.position       = desired_pos
            self.entry_spread   = current_spread
            self.steps_since_entry = 0
            pnl -= self._txn_cost(idx) * abs(desired_pos)

        # --- Per-step holding cost (reward shaping only) ---
        if self.position != 0:
            reward -= HOLDING_COST
            self.steps_since_entry += 1

        # --- Weak cointegration penalty (reward shaping only) ---
        if self._coint_pvalue > WEAK_COINT_THRESH:
            reward -= WEAK_COINT_PEN

        # --- Advance time ---
        self.current_step += 1
        self._maybe_refresh_coint()

        terminated = self.current_step >= self._episode_length

        # Force-close at episode end (the bar's market move is already in pnl)
        if terminated and self.position != 0:
            end_idx      = min(self.episode_start + self.current_step - 1, self._n - 1)
            reward      += (self._spread[end_idx] - self.entry_spread) * self.position
            pnl         -= self._txn_cost(end_idx) * abs(self.position)
            self.position = 0

        obs  = self._obs()
        info = {
            "spread":       float(current_spread),
            "position":     self.position,
            "coint_pvalue": self._coint_pvalue,
            "pnl":          float(pnl),
        }

        return obs, float(reward), terminated, False, info
