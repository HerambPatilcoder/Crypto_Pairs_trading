import duckdb
import pandas as pd

class TickStore:
    def __init__(self, path):
        self.con = duckdb.connect(path)
        self.con.execute("""
        CREATE TABLE IF NOT EXISTS ticks (
            timestamp TIMESTAMP,
            symbol VARCHAR,
            price DOUBLE,
            qty DOUBLE
        )
        """)

    def insert_tick(self, tick):
        df = pd.DataFrame([tick])
        self.con.execute("INSERT INTO ticks SELECT * FROM df")

    def fetch_ticks(self, symbol):
        return self.con.execute(
            "SELECT * FROM ticks WHERE symbol=? ORDER BY timestamp",
            [symbol]
        ).df()

    def insert_ohlc_bars(self, df):
        """
        Insert OHLC bars from uploaded CSV.
        Expected columns: timestamp, symbol, open, high, low, close, volume
        """
        # Convert OHLC bars to individual ticks (using close price)
        for _, row in df.iterrows():
            tick = {
                "timestamp": pd.to_datetime(row["timestamp"]),
                "symbol": str(row["symbol"]).upper(),
                "price": float(row["close"]),
                "qty": float(row.get("volume", 0.0))
            }
            self.insert_tick(tick)