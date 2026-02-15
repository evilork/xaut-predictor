import requests
from datetime import datetime


class DataFetcher:

    def __init__(self):
        self.base = "https://api.coingecko.com/api/v3"

    def get_xaut_ohlc(self, days=90):
        try:
            import pandas as pd
            resp = requests.get(
                f"{self.base}/coins/tether-gold/ohlc",
                params={"vs_currency": "usd", "days": days},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            return df.sort_index()
        except Exception as e:
            print(f"OHLC error: {e}")
            return None

    def get_xaut_history(self, days=90):
        try:
            import pandas as pd
            resp = requests.get(
                f"{self.base}/coins/tether-gold/market_chart",
                params={"vs_currency": "usd", "days": days, "interval": "daily"},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            df = pd.DataFrame(data.get("prices", []), columns=["timestamp", "price"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            volumes = data.get("total_volumes", [])
            if volumes:
                vol_df = pd.DataFrame(volumes, columns=["timestamp", "volume"])
                vol_df["timestamp"] = pd.to_datetime(vol_df["timestamp"], unit="ms")
                vol_df.set_index("timestamp", inplace=True)
                df = df.join(vol_df, how="left")
            return df.sort_index()
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
