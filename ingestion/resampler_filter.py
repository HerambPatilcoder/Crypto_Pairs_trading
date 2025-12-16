def resample_ticks(df, rule):
    df = df.set_index("timestamp")

    ohlcv = df.resample(rule).agg({
        "price": ["first", "max", "min", "last"],
        "qty": "sum"
    })

    ohlcv.columns = ["open", "high", "low", "close", "volume"]
    return ohlcv.dropna()

def liquidity_filter(bars, min_volume):
    return bars[bars["volume"] >= min_volume]