import pandas as pd

def mean_reversion_backtest(z, entry_z=2.0, exit_z=0.1):
    z = z.dropna()

    if len(z) < 5:
        return 0.0, pd.Series([], dtype=float)

    position = 0
    pnl = 0.0
    equity_curve = []
    timestamps = []

    for i in range(1, len(z)):
        prev_z = z.iloc[i-1]
        curr_z = z.iloc[i]

        # Entry rules
        if prev_z > entry_z:
            position = -1
        elif prev_z < -entry_z:
            position = 1

        # Exit rule
        if abs(prev_z) < exit_z:
            position = 0

        pnl += position * (curr_z - prev_z)
        equity_curve.append(pnl)
        timestamps.append(z.index[i])

    return pnl, pd.Series(equity_curve, index=timestamps)