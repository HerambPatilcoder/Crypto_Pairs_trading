import asyncio
import threading
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import time
import pandas as pd

from ingestion.binance_websocket import BinanceFuturesWS
from ingestion.duckdb_storage import TickStore
from ingestion.resampler_filter import resample_ticks
from analytics.features import huber_hedge_ratio, ols_r2
from analytics.features import kalman_hedge_ratio
from analytics.features import spread_and_zscore
from analytics.features import adf_test
from analytics.features import rolling_corr
from analytics.features import AlertEngine
from analytics.mean_reversion_backtest import mean_reversion_backtest
from ingestion.resampler_filter import liquidity_filter
from analytics.features import cross_corr
from config import (
    SYMBOLS,
    TIMEFRAMES,
    DB_PATH,
    DEFAULT_WINDOW,
    DEFAULT_Z_THRESHOLD
)

# -------------------- STORAGE --------------------
store = TickStore(DB_PATH)

# -------------------- CALLBACK --------------------
def on_tick(tick):
    store.insert_tick(tick)

# -------------------- WEBSOCKET STARTER --------------------
def start_ws():
    ws = BinanceFuturesWS(SYMBOLS, on_tick)
    asyncio.run(ws.start())

if "ws_started" not in st.session_state:
    st.session_state["ws_started"] = True
    threading.Thread(target=start_ws, daemon=True).start()

# -------------------- STREAMLIT UI --------------------
st.set_page_config(
    layout="wide",
    page_title="Crypto Pairs Trading Analytics",
    page_icon="📈",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    /* Main title styling */
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(120deg, #1e3a8a 0%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    /* Subtitle styling */
    .subtitle {
        color: #64748b;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Metric card enhancement */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 600;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: #f5f5f5;
    }
    
    /* Alert boxes */
    .stAlert {
        border-radius: 10px;
        padding: 1rem;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-weight: 600;
    }
    
    /* Button styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 2rem;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Download button special styling */
    .stDownloadButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
    }
    
    /* Dataframe styling */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">📈 Crypto Pairs Trading Analytics</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Real-time statistical arbitrage monitoring with live Binance futures data</p>', unsafe_allow_html=True)

# Auto-refresh every 2 seconds for live data (only if not in backtest tab)
if "current_tab" not in st.session_state:
    st.session_state["current_tab"] = "Prices & Volume"

# Auto-refresh unless user explicitly disabled it
if "auto_refresh_enabled" not in st.session_state:
    st.session_state["auto_refresh_enabled"] = True

if st.session_state["auto_refresh_enabled"]:
    st_autorefresh(interval=2000, key="datarefresh")

# -------------------- SIDEBAR CONTROLS --------------------
with st.sidebar:
    st.markdown("### 🎯 Controls Panel")
    st.markdown("---")
    
    st.markdown("#### 🔄 Universe Selection")
    symbol_y = st.selectbox("Y (Dependent) Symbol", SYMBOLS, index=0)
    symbol_x = st.selectbox("X (Hedge) Symbol", SYMBOLS, index=1)

    st.markdown("---")
    st.markdown("#### 📤 Data Upload")
    uploaded_file = st.file_uploader(
        "Upload OHLC CSV (Optional)",
        type=["csv"],
        help="Upload historical OHLC data. Format: timestamp,symbol,open,high,low,close,volume"
    )
    
    if uploaded_file is not None:
        try:
            upload_df = pd.read_csv(uploaded_file)
            required_cols = ["timestamp", "symbol", "open", "high", "low", "close"]
            
            if all(col in upload_df.columns for col in required_cols):
                # Insert into DuckDB
                store.insert_ohlc_bars(upload_df)
                st.success(f"✅ Uploaded {len(upload_df)} bars successfully!")
            else:
                st.error(f"❌ CSV must contain: {', '.join(required_cols)}")
        except Exception as e:
            st.error(f"❌ Upload failed: {str(e)}")

    st.markdown("---")
    st.markdown("#### 🔍 Filters")
    min_volume = st.number_input(
        "Min Volume Filter",
        min_value=0.0,
        max_value=10000.0,
        value=0.0,
        step=10.0,
        help="Filter out bars with volume below this threshold"
    )

    st.markdown("---")
    st.markdown("#### 📊 Analytics Settings")
    timeframe = st.selectbox(
        "Resample Timeframe",
        list(TIMEFRAMES.keys()),
        help="Controls OHLC bar aggregation.",
    )
    window = st.slider(
        "Rolling Window (bars)",
        20,
        200,
        DEFAULT_WINDOW,
        help="Window used for z-score and rolling correlation.",
    )
    z_thresh = st.slider(
        "Z-Score Alert Threshold",
        1.0,
        3.0,
        DEFAULT_Z_THRESHOLD,
        step=0.1,
        help="Alerts when |z| exceeds this threshold.",
    )

    st.markdown("---")
    st.markdown("#### 🚨 Alert Configuration")
    enable_spread_alert = st.checkbox(
        "Enable Spread Alert",
        value=False,
        help="Alert when spread width exceeds threshold"
    )
    spread_thresh = None
    if enable_spread_alert:
        spread_thresh = st.number_input(
            "Spread Width Threshold",
            min_value=0.0,
            value=100.0,
            step=10.0
        )
    
    enable_corr_alert = st.checkbox(
        "Enable Correlation Alert",
        value=False,
        help="Alert when correlation drops below threshold"
    )
    corr_thresh = None
    if enable_corr_alert:
        corr_thresh = st.slider(
            "Min Correlation Threshold",
            0.0,
            1.0,
            0.7,
            step=0.05
        )
    
    use_kalman = st.checkbox(
        "Use Kalman Hedge Ratio",
        value=False,
        help="If unchecked, robust Huber regression is used.",
    )

    st.markdown("---")
    st.markdown("#### ⚡ Auto-Refresh")
    auto_refresh_toggle = st.checkbox(
        "Enable Auto-Refresh (2s)",
        value=st.session_state["auto_refresh_enabled"],
        help="Automatically refresh live data every 2 seconds. Disable when running backtest.",
    )
    if auto_refresh_toggle != st.session_state["auto_refresh_enabled"]:
        st.session_state["auto_refresh_enabled"] = auto_refresh_toggle
        st.rerun()
    
    st.markdown("---")
    st.markdown("#### 📊 Data Status")
    
# -------------------- LOAD DATA --------------------
df_y = store.fetch_ticks(symbol_y.upper())
df_x = store.fetch_ticks(symbol_x.upper())

# Display data status in sidebar
with st.sidebar:
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric(f"{symbol_y.upper()}", f"{len(df_y)}", delta="ticks", delta_color="off")
    with col_b:
        st.metric(f"{symbol_x.upper()}", f"{len(df_x)}", delta="ticks", delta_color="off")
    
    st.markdown("---")
    st.info("💡 **Tip:** Keep the app open to accumulate live data. Larger windows need more history.")

# The size of data must be 5 ticks at least to perform analytics
if len(df_y) < 5 or len(df_x) < 5:
    st.warning("⏳ Collecting live data from Binance... please wait a few seconds.")
    st.info("💡 The dashboard will auto-update once enough ticks arrive.")
    st.stop()

# -------------------- RESAMPLE --------------------
bars_y = resample_ticks(df_y, TIMEFRAMES[timeframe])
bars_x = resample_ticks(df_x, TIMEFRAMES[timeframe])

# Apply liquidity filter if specified
if min_volume > 0:
    bars_y = liquidity_filter(bars_y, min_volume)
    bars_x = liquidity_filter(bars_x, min_volume)
    st.sidebar.caption(f"Filtered to {len(bars_y)} / {len(bars_x)} bars")

common_index = bars_y.index.intersection(bars_x.index)

# Require enough overlapping bars for meaningful analytics
if len(common_index) < 5:
    st.warning("Not enough overlapping resampled bars yet for analytics. Waiting for more data...")
    st.dataframe(bars_y.tail(10), width='stretch')
    st.dataframe(bars_x.tail(10), width='stretch')
    st.stop()

y = bars_y.loc[common_index]["close"]
x = bars_x.loc[common_index]["close"]

# -------------------- ANALYTICS --------------------
effective_window = min(window, len(common_index) - 1)

if use_kalman:
    hr_series = kalman_hedge_ratio(y, x)
    hr = hr_series[-1]
else:
    hr = huber_hedge_ratio(y, x)

spread, z = spread_and_zscore(y, x, hr, effective_window)
adf_stat, adf_p = adf_test(spread)
corr = rolling_corr(y, x, effective_window)
r2 = ols_r2(y, x)

# -------------------- ALERT --------------------
alert_engine = AlertEngine()

# Check all enabled alerts
alerts = alert_engine.check_all(
    z, z_thresh,
    spread=spread if enable_spread_alert else None,
    spread_thresh=spread_thresh,
    corr=corr if enable_corr_alert else None,
    corr_thresh=corr_thresh
)

if alerts:
    for alert_type, value, threshold in alerts:
        if alert_type == "Z-Score":
            st.error(f"🚨 {alert_type} Alert: {value:.2f} (threshold {threshold:.1f})")
        elif alert_type == "Spread Width":
            st.error(f"🚨 {alert_type} Alert: {value:.2f} exceeds {threshold:.1f}")
        elif alert_type == "Correlation Drop":
            st.error(f"🚨 {alert_type} Alert: {value:.3f} below {threshold:.2f}")
else:
    st.success(f"All monitored metrics within thresholds")

# -------------------- SUMMARY METRICS --------------------
st.markdown("### 📊 Summary Statistics")
st.caption("Key metrics for pair trading analysis")
st.markdown("")

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric(
        "⚖️ Hedge Ratio",
        f"{hr:.4f}",
        help="Optimal hedge ratio between the pair"
    )
with m2:
    st.metric(
        "📈 ADF p-value",
        f"{adf_p:.4f}",
        delta="Stationary" if adf_p < 0.05 else "Non-stationary",
        delta_color="normal" if adf_p < 0.05 else "inverse",
        help="Lower is better (< 0.05 indicates stationarity)"
    )
with m3:
    z_value = z.iloc[-1]
    st.metric(
        "🎯 Latest Z-Score",
        f"{z_value:.2f}",
        delta="Signal" if abs(z_value) > z_thresh else "Normal",
        delta_color="inverse" if abs(z_value) > z_thresh else "normal",
        help="Standardized spread deviation"
    )
with m4:
    st.metric(
        "📐 R²",
        f"{r2:.3f}",
        delta=f"{r2*100:.1f}% fit",
        delta_color="normal",
        help="Goodness of fit between the pair"
    )

# Additional stats row
m5, m6, m7, m8 = st.columns(4)
with m5:
    st.metric(
        "📊 Spread Mean",
        f"{spread.mean():.2f}",
        help="Average spread value"
    )
with m6:
    st.metric(
        "📏 Spread Std",
        f"{spread.std():.2f}",
        help="Spread volatility"
    )
with m7:
    st.metric(
        "🔗 Correlation",
        f"{corr.iloc[-1]:.3f}" if len(corr.dropna()) > 0 else "N/A",
        help="Latest rolling correlation"
    )
with m8:
    st.metric(
        "📦 Data Points",
        f"{len(common_index)}",
        help="Number of overlapping bars"
    )

st.markdown("")
st.markdown("---")

# -------------------- TABS LAYOUT --------------------
tab_overview, tab_spread, tab_corr, tab_backtest = st.tabs([
    "📈 Prices & Volume",
    "📊 Spread & Z-Score", 
    "🔗 Correlation Analysis",
    "💰 Backtest & Export"
])

with tab_overview:
    st.markdown("### 💹 Individual Asset Price Action")
    st.caption(f"Showing last 50 bars at **{timeframe}** timeframe | Total overlapping bars: **{len(common_index)}**")
    st.markdown("")

    st.markdown("### Individual Underlying Price")

    col_a, col_b = st.columns(2)

    with col_a:
        st.caption(f"{symbol_y.upper()}")
        ohlc_y = bars_y.tail(50).reset_index()
        fig_y = go.Figure(
            data=[
                go.Candlestick(
                    x=ohlc_y["timestamp"],
                    open=ohlc_y["open"],
                    high=ohlc_y["high"],
                    low=ohlc_y["low"],
                    close=ohlc_y["close"],
                    name=f"{symbol_y.upper()}",
                )
            ]
        )
        fig_y.update_layout(xaxis_title="Time", yaxis_title="Price")
        st.plotly_chart(fig_y, width='stretch')

    with col_b:
        st.caption(f"{symbol_x.upper()} ")
        ohlc_x = bars_x.tail(50).reset_index()
        fig_x = go.Figure(
            data=[
                go.Candlestick(
                    x=ohlc_x["timestamp"],
                    open=ohlc_x["open"],
                    high=ohlc_x["high"],
                    low=ohlc_x["low"],
                    close=ohlc_x["close"],
                    name=f"{symbol_x.upper()}",
                )
            ]
        )
        fig_x.update_layout(xaxis_title="Time", yaxis_title="Price")
        st.plotly_chart(fig_x, width='stretch')

    st.markdown("")
    st.markdown("### 📋 Recent Trading Activity")
    vol_cols = st.columns(2)
    with vol_cols[0]:
        st.caption(f"{symbol_y.upper()} last 20 bars")
        st.dataframe(bars_y.tail(20), width='stretch')
    with vol_cols[1]:
        st.caption(f"{symbol_x.upper()} last 20 bars")
        st.dataframe(bars_x.tail(20), width='stretch')

with tab_spread:
    st.markdown("### 📉 Spread & Z-Score Analysis")
    st.caption("Monitor mean-reversion opportunities when |z| exceeds threshold")
    st.markdown("")
    
    # Trading Signal Summary at the top
    current_z = z.iloc[-1]
    if current_z < -z_thresh:
        st.success(f"🟢 **LONG Signal** - Z-Score: {current_z:.2f} (Spread is low, buy the spread)")
    elif current_z > z_thresh:
        st.error(f"🔴 **SHORT Signal** - Z-Score: {current_z:.2f} (Spread is high, sell the spread)")
    else:
        st.info(f"⚪ **NEUTRAL** - Z-Score: {current_z:.2f} (No signal, wait for opportunity)")
    
    st.markdown("")
    
    # ADF Test Trigger Button
    col_adf1, col_adf2 = st.columns([1, 3])
    with col_adf1:
        if st.button("🔬 Run ADF Test", help="Test spread for stationarity"):
            st.session_state["show_adf_details"] = True
    
    if st.session_state.get("show_adf_details", False):
        with col_adf2:
            if adf_p < 0.05:
                st.success(f"✅ Spread is stationary (p-value: {adf_p:.4f} < 0.05)")
            else:
                st.warning(f"⚠️ Spread may not be stationary (p-value: {adf_p:.4f} >= 0.05)")
    
    st.markdown("---")
    
    # Add signal markers on spread
    long_signals = z[z < -z_thresh]
    short_signals = z[z > z_thresh]
    
    # st.plotly_chart(spread_fig, width='stretch')
    
    # st.markdown("")
    
    # Simple Z-Score Chart with colored zones
    st.markdown("#### 🎯 Z-Score (Trading Signals)")
    st.caption("Green zone = Long opportunity | Red zone = Short opportunity")
    
    z_fig = go.Figure()
    
    # Z-Score line
    z_fig.add_trace(go.Scatter(
        x=z.index,
        y=z,
        name="Z-Score",
        line=dict(color='purple', width=2)
    ))
    
    # Colored background zones
    z_fig.add_hrect(
        y0=z_thresh, y1=z.max() if len(z.dropna()) > 0 else 3,
        fillcolor="red", opacity=0.15,
        annotation_text="SHORT ZONE",
        annotation_position="top right"
    )
    
    z_fig.add_hrect(
        y0=-z_thresh, y1=z.min() if len(z.dropna()) > 0 else -3,
        fillcolor="green", opacity=0.15,
        annotation_text="LONG ZONE",
        annotation_position="bottom right"
    )
    
    # Threshold lines
    z_fig.add_hline(y=z_thresh, line_dash="dash", line_color="red")
    z_fig.add_hline(y=-z_thresh, line_dash="dash", line_color="green")
    z_fig.add_hline(y=0, line_dash="dot", line_color="gray")
    
    z_fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Z-Score",
        hovermode='x unified',
        showlegend=False
    )
    
    st.plotly_chart(z_fig, width='stretch')
    
    # Signal count summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🟢 Long Signals", len(long_signals))
    with col2:
        st.metric("🔴 Short Signals", len(short_signals))
    with col3:
        st.metric("Total Bars", len(common_index))

with tab_corr:
    st.markdown("### 🔗 Relationship Strength Analysis")
    st.caption("Track how strongly the pair moves together over time")
    st.markdown("")

    corr_fig = go.Figure()
    corr_fig.update_layout(title="Rolling Correlation over Time", xaxis_title="Time", yaxis_title="Correlation")
    corr_fig.add_trace(go.Scatter(x=corr.index, y=corr, name="Rolling Correlation"))
    st.plotly_chart(corr_fig, width='stretch')

    lags, corr_vals = cross_corr(y, x)
    heatmap_fig = go.Figure(
        data=go.Heatmap(
            z=[corr_vals],
            x=list(lags),
            y=["Cross-Corr"],
            colorscale="RdBu",
        )
    )
    heatmap_fig.update_layout(title="Cross-Correlation Heatmap (lags in bars)")
    st.plotly_chart(heatmap_fig, width='stretch')

with tab_backtest:
    st.markdown("### 💰 Mean-Reversion Strategy Backtest")
    st.caption("Test your strategy parameters on historical z-score data")
    st.markdown("")
    
    st.info("💡 **Pro Tip:** Disable auto-refresh in the sidebar before running backtest to avoid interruption.")
    st.markdown("")
    
    # Backtest parameters
    col_entry, col_exit = st.columns(2)
    with col_entry:
        entry_z = st.number_input("Entry Z-Score", 1.0, 5.0, 2.0, 0.1, help="Enter position when |z| exceeds this")
    with col_exit:
        exit_z = st.number_input("Exit Z-Score", 0.0, 2.0, 0.1, 0.1, help="Exit position when |z| falls below this")
    
    if st.button("▶️ Run Mean-Reversion Backtest", type="primary"):
        # Disable auto-refresh when backtest runs
        if st.session_state["auto_refresh_enabled"]:
            st.warning("Auto-refresh is enabled. Results may refresh before completion. Consider disabling it.")
        
        pnl, equity = mean_reversion_backtest(z, entry_z=entry_z, exit_z=exit_z)
        
        col_pnl, col_trades = st.columns(2)
        col_pnl.metric("Total PnL (z-units)", f"{pnl:.4f}")
        col_trades.metric("Data Points", len(equity))
        
        if len(equity) > 0:
            # Plot equity curve
            equity_fig = go.Figure()
            equity_fig.add_trace(go.Scatter(
                x=equity.index, 
                y=equity, 
                name="Cumulative PnL",
                fill='tozeroy',
                line=dict(color='green' if pnl > 0 else 'red')
            ))
            equity_fig.add_hline(y=0, line_dash="dash", line_color="gray")
            equity_fig.update_layout(
                title="Backtest Equity Curve",
                xaxis_title="Time",
                yaxis_title="Cumulative PnL (z-units)"
            )
            st.plotly_chart(equity_fig, width='stretch')
        else:
            st.warning("Not enough data to generate equity curve.")
    
    st.markdown("---")
    st.markdown("### 📥 Export Analytics Data")
    st.caption("Download complete time-series for further analysis")
    st.markdown("")

    export_df = (
        spread.rename("spread")
        .to_frame()
        .join(z.rename("z_score"))
        .join(corr.rename("rolling_corr"))
    )
    export_df.index.name = "timestamp"

    st.caption("Preview of exported analytics time-series")
    st.dataframe(export_df.tail(20), width='stretch')

    st.download_button(
        "Download Analytics CSV",
        data=export_df.reset_index().to_csv(index=False),
        file_name="pair_analytics.csv",
        mime="text/csv",
    )
