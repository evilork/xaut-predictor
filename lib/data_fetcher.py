import requests
from datetime import datetime
import time


class DataFetcher:

    def __init__(self):
        self.base = "https://api.coingecko.com/api/v3"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json"
        }

    def _get(self, url, params=None, retries=3):
        for i in range(retries):
            try:
                resp = requests.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=20
                )
                if resp.status_code == 429:
                    time.sleep(2)
                    continue
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                print(f"Attempt {i+1} failed: {e}")
                if i < retries - 1:
                    time.sleep(1)
        return None

    def get_xaut_ohlc(self, days=90):
        try:
            raw = self._get(
                f"{self.base}/coins/tether-gold/ohlc",
                params={"vs_currency": "usd", "days": days}
            )
            if not raw or not isinstance(raw, list) or len(raw) < 10:
                return None

            data = []
            for row in raw:
                data.append({
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4])
                })
            return data
        except Exception as e:
            print(f"OHLC error: {e}")
            return None

    def get_xaut_history(self, days=90):
        try:
            raw = self._get(
                f"{self.base}/coins/tether-gold/market_chart",
                params={"vs_currency": "usd", "days": days, "interval": "daily"}
            )
            if not raw:
                return None

            prices = raw.get("prices", [])
            if len(prices) < 10:
                return None

            data = []
            for row in prices:
                p = float(row[1])
                data.append({"open": p, "high": p, "low": p, "close": p})
            return data
        except Exception as e:
            print(f"History error: {e}")
            return None

    def get_gold_fallback(self):
        """Запасной источник — через другой API"""
        try:
            raw = self._get(
                "https://api.coingecko.com/api/v3/coins/tether-gold/market_chart",
                params={"vs_currency": "usd", "days": 30, "interval": "daily"}
            )
            if not raw:
                return None

            prices = raw.get("prices", [])
            if len(prices) < 10:
                return None

            data = []
            for row in prices:
                p = float(row[1])
                data.append({"open": p, "high": p, "low": p, "close": p})
            return data
        except:
            return None

    def get_current_price(self):
        try:
            raw = self._get(
                f"{self.base}/simple/price",
                params={
                    "ids": "tether-gold",
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_24hr_vol": "true",
                    "include_last_updated_at": "true"
                }
            )
            if not raw:
                return None

            d = raw.get("tether-gold", {})
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
            raw = self._get("https://api.alternative.me/fng/?limit=7")
            if not raw:
                return []
            return [
                {
                    "value": int(d["value"]),
                    "label": d["value_classification"],
                    "date": datetime.fromtimestamp(
                        int(d["timestamp"])
                    ).strftime("%Y-%m-%d")
                }
                for d in raw.get("data", [])
            ]
        except:
            return []
