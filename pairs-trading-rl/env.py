import warnings
import numpy as np
import yfinance as yf
import gymnasium as gym
from gymnasium import spaces
from statsmodels.tsa.stattools import coint

warnings.filterwarnings("ignore")

HEDGE_RATIO      = 2.2304
EPISODE_LENGTH   = 252          # ~1 trading year
COINT_WINDOW     = 60           # days used for rolling cointegration
COINT_INTERVAL   = 20           # recalculate every N steps
HOLDING_COST     = 0.005        # per step while position is open
WEAK_COINT_PEN   = 0.01         # penalty when rolling p-value > threshold
WEAK_COINT_THRESH = 0.1
HOLD_NORM        = 252          # fixed normalizer for the steps-since-entry obs.
                                # MUST stay constant across train/eval — episode
                                # length varies by phase, so dividing by it would
                                # feed the policy a differently-scaled feature at
                                # test time than it saw in training.


class PairsTradingEnv(gym.Env):
    """
    Pairs trading environment for a cointegrated pair (ticker1, ticker2).

    Spread = ticker1 - hedge_ratio * ticker2

    Actions:
        0 = go flat  (close any open position)
        1 = long spread
        2 = short spread

    Observation (4 floats):
        [z-score, position (-1/0/1), min(steps_since_entry / HOLD_NORM, 1), coint_p_value]
    """

    metadata = {"render_modes": []}

    def __init__(self, render_mode=None,
                 start_date="2023-01-01", end_date="2025-01-01",
                 episode_length=None,
                 ticker1="GLD", ticker2="RTX", hedge_ratio=HEDGE_RATIO,
                 preloaded: dict | None = None):
        """
        Parameters
        ----------
        preloaded : optional dict with keys 'p1', 'p2', 'dates' (numpy arrays /
                    DatetimeIndex).  When supplied the env skips yfinance and uses
                    these arrays directly — useful in walk-forward loops where data
                    is already downloaded.
        """
        super().__init__()

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
            return 0.0
        try:
            _, pval, _ = coint(self._p1[lo:idx+1], self._p2[lo:idx+1])
            return float(np.clip(pval, 0.0, 1.0))
        except Exception:
            return 1.0

    def _maybe_refresh_coint(self):
        self._steps_since_coint += 1
        if self._steps_since_coint >= COINT_INTERVAL:
            idx = self.episode_start + self.current_step
            self._coint_pvalue      = self._coint_pvalue_at(idx)
            self._steps_since_coint = 0

    def _obs(self) -> np.ndarray:
        idx    = min(self.episode_start + self.current_step, self._n - 1)
        zscore = np.clip(self._zscore_at(idx), -5.0, 5.0)
        held   = float(np.clip(self.steps_since_entry / HOLD_NORM, 0.0, 1.0))
        return np.array(
            [zscore,
             float(self.position),
             held,
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

        # --- Close position if direction changes or going flat ---
        if self.position != 0 and desired_pos != self.position:
            reward += (current_spread - self.entry_spread) * self.position
            zscore_now = self._zscore_at(idx)
            if -0.5 <= zscore_now <= 0.5:
                reward += 2.0
            self.position       = 0
            self.steps_since_entry = 0

        # --- Open new position ---
        if desired_pos != 0 and self.position == 0:
            self.position       = desired_pos
            self.entry_spread   = current_spread
            self.steps_since_entry = 0

        # --- Per-step holding cost ---
        if self.position != 0:
            reward -= HOLDING_COST
            self.steps_since_entry += 1

        # --- Weak cointegration penalty ---
        if self._coint_pvalue > WEAK_COINT_THRESH:
            reward -= WEAK_COINT_PEN

        # --- Advance time ---
        self.current_step += 1
        self._maybe_refresh_coint()

        terminated = self.current_step >= self._episode_length

        # Force-close at episode end
        if terminated and self.position != 0:
            end_idx      = min(self.episode_start + self.current_step - 1, self._n - 1)
            reward      += (self._spread[end_idx] - self.entry_spread) * self.position
            self.position = 0

        obs  = self._obs()
        info = {
            "spread":       float(current_spread),
            "position":     self.position,
            "coint_pvalue": self._coint_pvalue,
        }

        return obs, float(reward), terminated, False, info
