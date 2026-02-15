import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from data_fetcher import DataFetcher
from indicators import Indicators


class XAUTPredictor:

    def __init__(self):
        self.fetcher = DataFetcher()

    def linear_regression(self, x, y):
        n = len(x)
        if n < 2:
            return 0, 0
        sx = sum(x)
        sy = sum(y)
        sxy = sum(a * b for a, b in zip(x, y))
        sxx = sum(a * a for a in x)
        denom = n * sxx - sx * sx
        if denom == 0:
            return 0, sum(y) / n
        slope = (n * sxy - sx * sy) / denom
        intercept = (sy - slope * sx) / n
        return slope, intercept

    def weighted_moving_predict(self, prices, weights=None):
        n = min(len(prices), 10)
        recent = prices[-n:]
        if weights is None:
            weights = list(range(1, n + 1))
        total_w = sum(weights[-n:])
        return sum(p * w for p, w in zip(recent, weights[-n:])) / total_w

    def ema_predict(self, prices):
        ema5 = Indicators.ema(prices, 5)
        ema10 = Indicators.ema(prices, 10)
        last_price = prices[-1]
        trend = ema5[-1] - ema10[-1]
        return last_price + trend

    def regression_predict(self, prices):
        n = min(len(prices), 20)
        recent = prices[-n:]
        x = list(range(n))
        slope, intercept = self.linear_regression(x, recent)
        return slope * n + intercept

    def momentum_predict(self, prices):
        if len(prices) < 6:
            return prices[-1]
        changes = []
        for i in range(-5, 0):
            if prices[i-1] != 0:
                changes.append((prices[i] - prices[i-1]) / prices[i-1])
        if not changes:
            return prices[-1]
        weights = [1, 1, 2, 2, 3]
        avg_change = sum(c * w for c, w in zip(changes, weights)) / sum(weights)
        return prices[-1] * (1 + avg_change)

    def mean_reversion_predict(self, prices):
        n = min(len(prices), 20)
        recent = prices[-n:]
        mean = sum(recent) / len(recent)
        last = prices[-1]
        return last + (mean - last) * 0.15

    def ensemble_predict(self, prices):
        predictions = {
            "weighted_ma": self.weighted_moving_predict(prices),
            "ema_trend": self.ema_predict(prices),
            "linear_regression": self.regression_predict(prices),
            "momentum": self.momentum_predict(prices),
            "mean_reversion": self.mean_reversion_predict(prices),
        }

        weights = {
            "weighted_ma": 0.20,
            "ema_trend": 0.25,
            "linear_regression": 0.25,
            "momentum": 0.20,
            "mean_reversion": 0.10,
        }

        ensemble = sum(predictions[k] * weights[k] for k in predictions)
        predictions["ensemble"] = round(ensemble, 2)

        for k in predictions:
            predictions[k] = round(predictions[k], 2)

        return predictions

    def calculate_accuracy(self, prices):
        if len(prices) < 30:
            return {}

        errors = {"weighted_ma": [], "ema_trend": [], "linear_regression": [],
                  "momentum": [], "mean_reversion": [], "ensemble": []}

        for i in range(20, len(prices) - 1):
            subset = prices[:i]
            actual = prices[i]
            preds = self.ensemble_predict(subset)

            for name in errors:
                if name in preds:
                    errors[name].append(abs(preds[name] - actual))

        metrics = {}
        for name, errs in errors.items():
            if errs:
                mae = sum(errs) / len(errs)
                metrics[name] = {"mae": round(mae, 2)}

        return metrics

    def run(self):
        data = self.fetcher.get_xaut_ohlc(days=90)

        if data is None or len(data) < 30:
            data = self.fetcher.get_xaut_history(days=90)

        if data is None or len(data) < 30:
            return {"error": "Недостаточно данных. Попробуйте позже."}

        closes = [d["close"] for d in data]

        # Прогнозы
        predictions = self.ensemble_predict(closes)
        ensemble = predictions["ensemble"]

        # Точность
        metrics = self.calculate_accuracy(closes)

        # Текущая цена
        current = self.fetcher.get_current_price()
        current_price = current["price"] if current else closes[-1]

        # Изменение
        change = 0
        if current_price > 0:
            change = round(((ensemble - current_price) / current_price) * 100, 4)

        if change > 0.3:
            direction = "📈 РОСТ"
        elif change < -0.3:
            direction = "📉 ПАДЕНИЕ"
        else:
            direction = "➡️ БОКОВИК"

        # Уровни
        recent_30 = closes[-30:]
        support = round(min(recent_30), 2)
        resistance = round(max(recent_30), 2)

        # Индикаторы и сигналы
        indicators_data, signals = Indicators.analyze(data)

        # Fear & Greed
        fg = self.fetcher.get_fear_greed()

        return {
            "current_price": current_price,
            "current_market": current,
            "predictions": predictions,
            "ensemble": ensemble,
            "change_pct": change,
            "direction": direction,
            "support": support,
            "resistance": resistance,
            "indicators": indicators_data,
            "signals": signals,
            "metrics": metrics,
            "fear_greed": fg,
            "data_points": len(data),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        }
