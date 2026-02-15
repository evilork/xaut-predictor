import requests
from datetime import datetime


class DataFetcher:

    def __init__(self):
        self.base = "https://api.coingecko.com/api/v3"

    def get_xaut_ohlc(self, days=90):
        try:
            resp = requests.get(
                f"{self.base}/coins/tether-gold/ohlc",
                params={"vs_currency": "usd", "days": days},
                timeout=15
            )
            resp.raise_for_status()
            raw = resp.json()

            if not isinstance(raw, list) or len(raw) < 10:
                return None

            data = []
            for row in raw:
                data.append({
                    "timestamp": row[0],
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4]
                })
            return data
        except Exception as e:
            print(f"OHLC error: {e}")
            return None

    def get_xaut_history(self, days=90):
        try:
            resp = requests.get(
                f"{self.base}/coins/tether-gold/market_chart",
                params={"vs_currency": "usd", "days": days, "interval": "daily"},
                timeout=15
            )
            resp.raise_for_status()
            raw = resp.json()
            prices = raw.get("prices", [])

            if len(prices) < 10:
                return None

            data = []
            for row in prices:
                p = row[1]
                data.append({
                    "timestamp": row[0],
                    "open": p, "high": p, "low": p, "close": p
                })
            return data
        except Exception as e:
            print(f"History error: {e}")
            return None

    def get_current_price(self):
        try:
            resp = requests.get(
                f"{self.base}/simple/price",
                params={
                    "ids": "tether-gold",
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_24hr_vol": "true",
                    "include_last_updated_at": "true"
                },
                timeout=10
            )
            resp.raise_for_status()
            d = resp.json().get("tether-gold", {})
            return {
                "price": d.get("usd", 0),
                "change_24h": round(d.get("usd_24h_change", 0), 2),
                "volume_24h": d.get("usd_24h_vol", 0),
                "last_updated": datetime.fromtimestamp(
                    d.get("last_updated_at", 0)
                ).strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"Price error: {e}")
            return None

    def get_fear_greed(self):
        try:
            resp = requests.get(
                "https://api.alternative.me/fng/?limit=7",
                timeout=10
            )
            resp.raise_for_status()
            return [
                {
                    "value": int(d["value"]),
                    "label": d["value_classification"],
                    "date": datetime.fromtimestamp(int(d["timestamp"])).strftime("%Y-%m-%d")
                }
                for d in resp.json().get("data", [])
            ]
        except:
            return []
