"""
Deterministic policy evaluation shared by backtest.py and walk_forward.py.

A single, correct evaluation loop lives here so both entry points report the
same thing: realized P&L (net of transaction costs), not the shaped RL reward.
It also tracks trades by *position transitions*, which correctly handles direct
long<->short reversals (a single step closing one trade and opening another).
"""

from env import PairsTradingEnv, COINT_WINDOW


def run_episode(model, env: PairsTradingEnv):
    """Run one deterministic pass over the whole env window.

    The first ``COINT_WINDOW`` bars are used only as a look-back for the z-score
    and cointegration statistics; the agent starts trading right after them.

    Returns
    -------
    steps : list[dict]   {"date", "pnl", "position", "spread"}
        ``pnl`` is realized mark-to-market P&L in spread units, net of costs.
    trades : list[dict]  {"entry_date", "exit_date", "direction", "pnl"}
        ``pnl`` is net of round-trip transaction costs. By construction
        ``sum(t["pnl"] for t in trades) == sum(s["pnl"] for s in steps)``.
    """
    n_steps = env._n - COINT_WINDOW
    env._episode_length = n_steps
    obs, _ = env.reset(options={"episode_start": COINT_WINDOW})

    steps, trades = [], []
    open_trade = None
    prev_pos   = 0

    for step in range(n_steps):
        action, _ = model.predict(obs, deterministic=True)
        obs, _reward, terminated, _truncated, info = env.step(int(action))

        idx  = min(COINT_WINDOW + step, env._n - 1)
        date = env.dates[idx]
        pos  = info["position"]

        steps.append({
            "date":     date,
            "pnl":      info["pnl"],
            "position": pos,
            "spread":   info["spread"],
        })

        if pos != prev_pos:
            # Close whatever was open (covers flat-out and direct reversal).
            if open_trade is not None:
                sign  = 1 if open_trade["direction"] == "long" else -1
                gross = (info["spread"] - open_trade["entry_spread"]) * sign
                cost  = env._txn_cost(open_trade["entry_idx"]) + env._txn_cost(idx)
                trades.append({
                    "entry_date": open_trade["entry_date"],
                    "exit_date":  date,
                    "direction":  open_trade["direction"],
                    "pnl":        gross - cost,
                })
                open_trade = None
            # Open a new trade if we are now in a position.
            if pos != 0:
                open_trade = {
                    "entry_date":   date,
                    "entry_idx":    idx,
                    "direction":    "long" if pos == 1 else "short",
                    "entry_spread": env.entry_spread,
                }

        prev_pos = pos
        if terminated:
            break

    return steps, trades
