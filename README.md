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

## 🎨 Features

### Core Features
✅ **Live Data Ingestion**: Real-time Binance futures ticks via WebSocket  
✅ **Flexible Resampling**: 1-second, 1-minute, 5-minute OHLC bars  
✅ **OHLC CSV Upload**: Import historical data for extended analysis  
✅ **Dual Hedge Ratio Methods**: Huber (robust) and Kalman (dynamic)  
✅ **Spread & Z-Score**: Core mean-reversion metrics  
✅ **Statistical Tests**: ADF for stationarity, R² for fit quality  
✅ **Multi-Condition Alerts**: Z-score, spread width, correlation drop  
✅ **Liquidity Filtering**: Exclude low-volume bars  
✅ **Interactive Backtest**: Configurable entry/exit, equity curve visualization  
✅ **Data Export**: Download analytics time-series as CSV  

### UI Features
✅ **Auto-Refresh**: Live updates every 2 seconds (togglable)  
✅ **Symbol Selection**: Choose Y and X assets from configured pairs  
✅ **Tabbed Layout**: Organized sections for prices, spread, correlation, backtest  
✅ **Candlestick Charts**: OHLC visualization for both assets  
✅ **Alert Indicators**: Color-coded warnings when thresholds breached  
✅ **Responsive Controls**: Sliders, dropdowns, checkboxes with help text  

---

## 🎛️ User Guide

### Sidebar Controls

**Universe**
- **Y Symbol**: Dependent variable (e.g., BTCUSDT)
- **X Symbol**: Independent variable / hedge (e.g., ETHUSDT)

**Data Upload**
- Upload CSV with columns: `timestamp, symbol, open, high, low, close, volume`
- Optional: works alongside live data

**Filters**
- **Min Volume Filter**: Exclude bars with volume below threshold (0 = disabled)

**Analytics**
- **Resample Timeframe**: 1s, 1m, or 5m bar aggregation
- **Rolling Window**: Window size for z-score and correlation (20-200 bars)
- **Z-Score Alert Threshold**: Trigger alert when |z| exceeds this (1.0-3.0)

**Additional Alerts** (optional)
- **Spread Alert**: Enable + set width threshold
- **Correlation Alert**: Enable + set minimum correlation

**Hedge Ratio Method**
- ☐ Use Kalman Hedge Ratio (unchecked = Huber regression)

**Auto-Refresh**
- ☐ Enable Auto-Refresh (2s)
- Tip: Disable before running backtest

### Dashboard Tabs

**1. Prices & Volume**
- Side-by-side candlestick charts for Y and X symbols
- Recent bars tables (last 20)

**2. Spread & Z-Score**
- Z-score time series with alert threshold lines

**3. Correlation**
- Rolling correlation over time
- Cross-correlation heatmap (lag analysis)

**4. Backtest & Export**
- Configure entry/exit z-score thresholds
- Run backtest → see PnL and equity curve
- Preview analytics table
- Download full time-series as CSV

---


## 🧪 Design Decisions & Trade-offs

### Why DuckDB?
- **Embedded**: No separate database server needed
- **Fast**: Columnar storage, optimized for analytics queries
- **Simple**: SQL interface, easy to extend with indices/partitions
- **Trade-off**: Single-process file lock (not ideal for multi-process writes)
- **Future**: Could switch to PostgreSQL/TimescaleDB for production scale

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

## 📈 Scaling Considerations

**Current Design** (local, single-process):
- WebSocket thread writes to DuckDB
- Streamlit main thread reads from DuckDB
- Works for demo; potential lock contention at scale

**Production Enhancements**:

1. **Separate Ingestion Service**
   - Dedicated process for WebSocket → Storage
   - Use message queue (Kafka/Redis Streams) between ingestion and analytics
   - Horizontal scaling: multiple WebSocket clients for different symbols

2. **Read/Write Separation**
   - Writer: Single process owns DuckDB writes
   - Readers: Query via read-only connections or replicated DB
   - Alternative: Time-series DB (InfluxDB, TimescaleDB)

3. **Caching Layer**
   - Redis for recent bars and computed features
   - Reduces DB queries on every UI refresh

4. **Async Analytics**
   - Move heavy computations (ADF, backtest) to background workers
   - Return results via polling or WebSocket to frontend

5. **Data Retention**
   - Partition tables by date
   - Aggregate old data to reduce storage (tick → 1m → 1h → daily)

6. **Frontend**
   - Migrate to React + WebSocket for true real-time updates
   - Backend REST API (FastAPI) for analytics endpoints

---

## 🐛 Known Limitations

1. **DuckDB File Locking**
   - Issue: Multiple Streamlit instances or reruns can cause lock conflicts
   - Workaround: Kill stale processes (`lsof market.duckdb`, `kill PID`)
   - Fix: Implement connection pooling or separate read/write connections

2. **No Historical Data Persistence**
   - WebSocket runs in daemon thread; data lost on app restart
   - Solution: Background service to continuously write to DB, or upload historical CSVs

3. **Simplified Backtest**
   - PnL in z-units, not monetary terms
   - No transaction costs, slippage, or position sizing
   - Enhancement: Convert to dollar PnL using actual prices and position sizes

4. **Limited Symbol Universe**
   - Currently hardcoded to 2 symbols (BTC, ETH)
   - Enhancement: Dynamic symbol management, support for 10+ pairs

5. **No User Authentication**
   - Single-user local app
   - Production: Add auth, multi-tenancy

---

## 📦 Dependencies

- **streamlit**: Web UI framework
- **streamlit-autorefresh**: Auto-refresh functionality
- **websockets**: Async WebSocket client for Binance
- **pandas**: Data manipulation and time-series analysis
- **numpy**: Numerical computations
- **duckdb**: Embedded analytics database
- **plotly**: Interactive charting
- **statsmodels**: Statistical tests (ADF, OLS)
- **scikit-learn**: Huber regression

## 🎓 Further Enhancements (Future Work)

If I had more time, I would add:

1. **Johansen Cointegration Test**: More rigorous than ADF for pairs
2. **Half-Life Metric**: Ornstein-Uhlenbeck mean-reversion speed
3. **Volume-Weighted Charts**: Add volume bars below candlesticks
4. **Position Sizing**: Kelly criterion or risk-parity based allocation
5. **Multi-Pair Dashboard**: Compare 5-10 pairs simultaneously
6. **Alert Log**: Persistent table of alert history with timestamps
7. **Strategy Optimizer**: Grid search over entry/exit thresholds
8. **Drawdown Analysis**: Max drawdown, Sharpe ratio for backtest
9. **WebSocket Health Monitor**: Connection status indicator in UI
10. **Dark Mode**: UI theme toggle for trader preference

---

## 📄 License

This project was developed for educational and evaluation purposes. Not licensed for commercial use without permission.

---

## 👤 Author

Developed by Heramb Patil as part of a quantitative developer assignment.

**Contact**: [Your email/LinkedIn if you want to share]

---