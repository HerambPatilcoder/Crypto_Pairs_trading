import asyncio
import json
import websockets
from datetime import datetime

class BinanceFuturesWS:
    def __init__(self, symbols, on_tick):
        self.symbols = [s.lower() for s in symbols]
        self.on_tick = on_tick   

    async def _connect(self, symbol):
        url = f"wss://stream.binance.com:9443/ws/{symbol}@trade"
        async with websockets.connect(url) as ws:
            async for msg in ws:
                data = json.loads(msg)
                if data.get("e") == "trade":
                    tick = {
                        "timestamp": datetime.fromtimestamp(data["T"] / 1000),
                        "symbol": data["s"],
                        "price": float(data["p"]),
                        "qty": float(data["q"])
                    }
                    self.on_tick(tick)

    async def start(self):
        self.tasks = [asyncio.create_task(self._connect(s)) for s in self.symbols]
        await asyncio.gather(*self.tasks)


