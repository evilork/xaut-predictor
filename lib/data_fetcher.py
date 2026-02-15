import requests
from datetime import datetime
import time
import json


class DataFetcher:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9"
        })

    def _get(self, url, params=None, retries=2):
        for i in range(retries):
            try:
                resp = self.session.get(url, params=params, timeout=15)
                if resp.status_code == 429:
                    time.sleep(3)
                    continue
                if resp.status_code == 200:
                    return resp.json()
            except:
                if i < retries - 1:
                    time.sleep(1)
        return None

    def get_from_coingecko_ohlc(self):
        return self._get(
            "https://api.coingecko.com/api/v3/coins/tether-gold/ohlc",
            params={"vs_currency": "usd", "days": 90}
        )

    def get_from_coingecko_chart(self):
        return self._get(
            "https://api.coingecko.com/api/v3/coins/tether-gold/market_chart",
            params={"vs_currency": "usd", "days": 90, "interval": "daily"}
        )

    def get_from_coinpaprika(self):
        """Альтернативный API — CoinPaprika (бесплатный)"""
        raw = self._get(
            "https://api.coinpaprika.com/v1/tickers/xaut-tether-gold"
        )
        if not raw:
            return None

        price = raw.get("quotes", {}).get("USD", {}).get("price", 0)
        if price <= 0:
            return None

        # Получаем историю
        hist = self._get(
            "https://api.coinpaprika.com/v1/tickers/xaut-tether-gold/historical",
            params={"start": "2025-01-01", "interval": "1d"}
        )

        if hist and isinstance(hist, list) and len(hist) >= 10:
            data = []
            for row in hist:
                p = float(row.get("price", 0))
                if p > 0:
                    data.append({"open": p, "high": p, "low": p, "close": p})
            if len(data) >= 10:
                return data, price

        return None, price

    def get_from_livecoinwatch(self):
        """Ещё один альтернативный источник"""
        raw = self._get(
            "https://http-api.livecoinwatch.com/coins/single/history",
            params={"currency": "USD", "code": "XAUT", "start": int(time.time()*1000) - 90*86400*1000, "end": int(time.time()*1000)}
        )
        if raw and isinstance(raw, dict):
            history = raw.get("history", [])
            if len(history) >= 10:
                data = []
                for row in history:
                    p = float(row.get("rate", 0))
                    if p > 0:
                        data.append({"open": p, "high": p, "low": p, "close": p})
                return data
        return None

    def get_gold_price_proxy(self):
        """Используем XAU/USD через бесплатные forex API"""
        # Через exchangerate.host
        raw = self._get(
            "https://api.exchangerate.host/timeseries",
            params={
                "base": "XAU",
                "symbols": "USD",
                "start_date": "2025-01-01",
                "end_date": datetime.utcnow().strftime("%Y-%m-%d")
            }
        )
        if raw and raw.get("success") and raw.get("rates"):
            data = []
            for date_str in sorted(raw["rates"].keys()):
                rate = raw["rates"][date_str].get("USD", 0)
                if rate > 0:
                    data.append({"open": rate, "high": rate, "low": rate, "close": rate})
            if len(data) >= 10:
                return data
        return None

    def get_data(self):
        """Пробуем все источники по очереди"""

        # 1. CoinGecko OHLC
        raw = self.get_from_coingecko_ohlc()
        if raw and isinstance(raw, list) and len(raw) >= 10:
            data = []
            for row in raw:
                if isinstance(row, list) and len(row) >= 5:
                    data.append({
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4])
                    })
            if len(data) >= 10:
                return data, "coingecko_ohlc"

        # 2. CoinGecko Chart
        raw = self.get_from_coingecko_chart()
        if raw and isinstance(raw, dict):
            prices = raw.get("prices", [])
            if len(prices) >= 10:
                data = []
                for row in prices:
                    p = float(row[1])
                    data.append({"open": p, "high": p, "low": p, "close": p})
                return data, "coingecko_chart"

        # 3. CoinPaprika
        try:
            result = self.get_from_coinpaprika()
            if result:
                paprika_data, paprika_price = result
                if paprika_data and len(paprika_data) >= 10:
                    return paprika_data, "coinpaprika"
        except:
            pass

        # 4. Генерируем данные из текущей цены
        current = self.get_current_price()
        if current and current["price"] > 0:
            price = current["price"]
            # Создаём синтетические данные на основе текущей цены
            # с небольшими вариациями для работы индикаторов
            import random
            random.seed(42)
            data = []
            p = price * 0.95  # начинаем с 95% текущей цены
            for i in range(60):
                change = random.uniform(-0.008, 0.008)
                p = p * (1 + change)
                data.append({
                    "open": round(p * 0.999, 2),
                    "high": round(p * 1.003, 2),
                    "low": round(p * 0.997, 2),
                    "close": round(p, 2)
                })
            # Последняя цена = текущая
            data[-1]["close"] = price
            data[-1]["high"] = price * 1.001
            data[-1]["low"] = price * 0.999
            return data, "synthetic"

        return None, None

    def get_current_price(self):
        # CoinGecko
        raw = self._get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": "tether-gold",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
                "include_last_updated_at": "true"
            }
        )
        if raw and "tether-gold" in raw:
            d = raw["tether-gold"]
            return {
                "price": d.get("usd", 0),
                "change_24h": round(d.get("usd_24h_change", 0), 2),
                "volume_24h": d.get("usd_24h_vol", 0),
                "last_updated": datetime.fromtimestamp(
                    d.get("last_updated_at", 0)
                ).strftime("%Y-%m-%d %H:%M:%S")
            }

        # CoinPaprika fallback
        raw = self._get("https://api.coinpaprika.com/v1/tickers/xaut-tether-gold")
        if raw:
            usd = raw.get("quotes", {}).get("USD", {})
            return {
                "price": usd.get("price", 0),
                "change_24h": round(usd.get("percent_change_24h", 0), 2),
                "volume_24h": usd.get("volume_24h", 0),
                "last_updated": raw.get("last_updated", "")
            }

        return None

    def get_fear_greed(self):
        raw = self._get("https://api.alternative.me/fng/?limit=7")
        if not raw:
            return []
        try:
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
