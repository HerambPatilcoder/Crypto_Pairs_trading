Before moving ahead with the readme file. The question that will arise in your mind will be what is duckdb, why I used duckdb?
Firstly, it doesn't require any separate database server. Also, it's mainly build for analytics. It's SQL based and provides fast local analysis on large datasets and simplifies data pipelines with it's VIEW property. I backtested various strategies in my previous quant analyst internship.

# Crypto Pairs Trading Analytics Dashboard

A real-time quantitative analytics application for statistical arbitrage and mean-reversion trading strategies on cryptocurrency futures pairs. The system ingests live tick data from Binance WebSocket streams, computes statistical features, and provides an interactive dashboard for monitoring pair relationships and backtesting trading strategies.

## 🎯 Project Overview

This project was developed as part of a quantitative developer evaluation assignment. It demonstrates end-to-end capability in:
- Real-time data ingestion and storage
- Statistical analytics for pairs trading
- Interactive visualization and user controls
- Backtesting mean-reversion strategies
- Modular, extensible architecture

**Target Use Case**: Helper analytics for traders and researchers at a multi-frequency trading (MFT) firm trading statistical arbitrage, risk-premia harvesting, and market-making strategies across cash and derivatives.


### Component Responsibilities

**1. Data Ingestion** (`binance_websocket.py`)
- Establishes WebSocket connections to Binance futures trade streams
- Parses tick data: `{timestamp, symbol, price, qty}`
- Passes ticks to storage callback
- Handles multiple symbols concurrently via asyncio

**2. Storage** (`duckdb_storage.py`)
- DuckDB embedded database for tick storage
- Schema: `timestamp, symbol, price, qty`
- Methods: `insert_tick()`, `fetch_ticks()`, `insert_ohlc_bars()`
- Supports both live ingestion and CSV upload

**3. Resampling & Filtering** (`resampler_filter.py`)
- Converts tick data to OHLC bars at configurable intervals (1s, 1m, 5m)
- Liquidity filter: removes bars below minimum volume threshold
- Uses pandas resample with aggregation: `first, max, min, last, sum`

**4. Analytics** (`features.py`, `mean_reversion_backtest.py`)
- **Hedge Ratio**: Huber robust regression (default) or Kalman filter (time-varying)
- **Spread**: `spread = y - hedge_ratio * x`
- **Z-Score**: Rolling standardized spread `(spread - mean) / std`
- **ADF Test**: Augmented Dickey-Fuller for stationarity testing
- **Correlation**: Rolling Pearson correlation + cross-correlation at lags
- **R²**: OLS coefficient of determination
- **Alert Engine**: Multi-condition alerts (z-score, spread width, correlation drop)
- **Backtest**: Mean-reversion strategy with configurable entry/exit thresholds

**5. Frontend** (`app.py`)
- Streamlit-based interactive dashboard
- Four main tabs: Prices & Volume, Spread & Z-Score, Correlation, Backtest & Export
- Sidebar controls for symbol selection, timeframe, window, thresholds, filters
- Auto-refresh every 2 seconds (togglable)
- Real-time alerts and metric displays

---

## 📊 Analytics Methodology

### Hedge Ratio Estimation

**Huber Regression (Default)**:
- Robust to outliers compared to OLS
- Model: `y = β·x + ε`
- Returns coefficient β as hedge ratio

**Kalman Filter (Optional)**:
- Time-varying hedge ratio
- Useful when relationship between assets is non-stationary
- Tracks dynamic beta evolution

### Spread & Mean Reversion

**Spread Construction**:
```
spread(t) = y(t) - hedge_ratio * x(t)
```

**Z-Score**:
```
z(t) = (spread(t) - rolling_mean(spread)) / rolling_std(spread)
```

Interpretation:
- `|z| > 2`: Spread is unusually wide → potential mean-reversion opportunity
- `|z| < 0.5`: Spread near mean → exit signal

### Stationarity Testing

**ADF (Augmented Dickey-Fuller) Test**:
- Null hypothesis: spread has a unit root (non-stationary)
- p-value < 0.05 → reject null → spread is stationary → suitable for mean reversion
- Displayed in UI for quick assessment

### Correlation Analysis

**Rolling Correlation**:
- Measures linear relationship strength over moving window
- Helps identify regime changes (correlation breakdowns)

**Cross-Correlation**:
- Correlation at different time lags
- Detects lead-lag relationships between assets

### Mean-Reversion Backtest

**Strategy Logic**:
1. **Entry**: When `|z| > entry_threshold` (default 2.0)
   - `z > 2`: Short the spread (sell y, buy x)
   - `z < -2`: Long the spread (buy y, sell x)
2. **Exit**: When `|z| < exit_threshold` (default 0.1)
3. **PnL**: Cumulative change in z-score weighted by position

**Output**:
- Total PnL (in z-score units)
- Equity curve showing cumulative PnL evolution
- Number of trades/data points

**Limitations** (acknowledged):
- PnL in z-units, not dollar terms
- Ignores transaction costs, slippage
- No position sizing or risk management
- Simplified for demonstration purposes

---

## 🧪 Design Decisions & Trade-offs

### Why Huber Regression over OLS?
- **Robustness**: Less sensitive to outliers in price data
- **Stability**: More reliable hedge ratio during volatile periods
- **Trade-off**: Slightly slower computation
- **Alternative**: Kalman filter for time-varying relationships

### Why Z-Score for Mean Reversion?
- **Standardization**: Normalizes spread regardless of price levels
- **Intuitive**: Clear threshold interpretation (2σ rule)
- **Trade-off**: Assumes spread is normally distributed (may not hold)
- **Enhancement**: Could add Bollinger Bands or percentile-based signals

### Why Streamlit?
- **Rapid Development**: Built in ~1 day as required
- **Interactive**: Native widgets, auto-rerun on input change
- **Trade-off**: Not ideal for high-frequency updates (2s refresh is reasonable limit)
- **Production**: Would migrate to React + FastAPI for sub-second latency

### Architecture: Loose Coupling
- **Ingestion** → Storage → Analytics → UI are separate modules
- **Benefit**: Easy to swap components (e.g., CME data source, Redis storage)
- **Interfaces**:
  - DataSource: `start(callback)`
  - Storage: `insert_tick()`, `fetch_ticks()`
  - Analytics: Pure functions taking pandas Series/DataFrames

---
n if you want to share]

---
