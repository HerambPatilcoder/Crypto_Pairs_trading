import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
from sklearn.linear_model import HuberRegressor
import numpy as np

# For checking mean-reversion (Stationarity) using ADF test
def adf_test(series):
    stat, pvalue, *_ = adfuller(series.dropna())
    return stat, pvalue

# Calculating spread and its z-score
def spread_and_zscore(y, x, hr, window):
    spread = y - hr * x
    mean = spread.rolling(window).mean()
    std = spread.rolling(window).std()
    z = (spread - mean) / std
    return spread, z

# Calculating hedge ratio using Huber regression
def huber_hedge_ratio(y, x):
    model = HuberRegressor().fit(x.values.reshape(-1,1), y.values)
    return model.coef_[0]


# Calculating R-squared using standard OLS regression (y ~ alpha + beta * x)
def ols_r2(y, x):
    x_with_const = sm.add_constant(x.values)
    model = sm.OLS(y.values, x_with_const).fit()
    return model.rsquared


# Calculating time-varying hedge ratio using Kalman Filter
def kalman_hedge_ratio(y, x, delta=1e-4, R=0.01):
    """
    Returns time-varying hedge ratio using Kalman Filter
    """
    n = len(y)
    hr = np.zeros(n)

    P = 1.0
    Q = delta / (1 - delta)

    for t in range(n):
        if t > 0:
            P = P + Q

        # Measurement update
        y_hat = hr[t-1] * x.iloc[t] if t > 0 else 0
        e = y.iloc[t] - y_hat
        K = P * x.iloc[t] / (x.iloc[t]**2 * P + R)

        hr[t] = hr[t-1] + K * e if t > 0 else 0
        P = (1 - K * x.iloc[t]) * P

    return hr

# Calculating rolling correlation between two series
def rolling_corr(x, y, window):
    return x.rolling(window).corr(y)

# Alert engine to trigger alerts based on multiple conditions
class AlertEngine:
    def check(self, z, threshold):
        if len(z.dropna()) == 0:
            return False
        return abs(z.iloc[-1]) > threshold
    
    def check_spread(self, spread, threshold):
        """Alert when spread width exceeds threshold"""
        if len(spread.dropna()) == 0:
            return False
        return abs(spread.iloc[-1]) > threshold
    
    def check_correlation_drop(self, corr, threshold):
        """Alert when correlation drops below threshold"""
        if len(corr.dropna()) == 0:
            return False
        return corr.iloc[-1] < threshold
    
    def check_all(self, z, z_thresh, spread=None, spread_thresh=None, corr=None, corr_thresh=None):
        """Check multiple alert conditions and return triggered alerts"""
        alerts = []
        
        if self.check(z, z_thresh):
            alerts.append(("Z-Score", z.iloc[-1], z_thresh))
        
        if spread is not None and spread_thresh is not None:
            if self.check_spread(spread, spread_thresh):
                alerts.append(("Spread Width", spread.iloc[-1], spread_thresh))
        
        if corr is not None and corr_thresh is not None:
            if self.check_correlation_drop(corr, corr_thresh):
                alerts.append(("Correlation Drop", corr.iloc[-1], corr_thresh))
        
        return alerts
    
def cross_corr(x, y, max_lag=20):
    lags = range(-max_lag, max_lag + 1)
    corr = [x.corr(y.shift(lag)) for lag in lags]
    return lags, corr
