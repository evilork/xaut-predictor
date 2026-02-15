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

    def predict_next(self, prices, steps=1):
        """Прогноз на N шагов вперёд"""
        results = []
        current_prices = prices[:]

        for step in range(steps):
            wma = self._weighted_ma(current_prices)
            ema = self._ema_pred(current_prices)
            reg = self._regression_pred(current_prices)
            mom = self._momentum_pred(current_prices)
            rev = self._mean_reversion_pred(current_prices)

            ensemble = (
                wma * 0.20 +
                ema * 0.25 +
                reg * 0.25 +
                mom * 0.20 +
                rev * 0.10
            )

            results.append(round(ensemble, 2))
            current_prices.append(ensemble)

        return results

    def _weighted_ma(self, prices):
        n = min(len(prices), 10)
        recent = prices[-n:]
        weights = list(range(1, n + 1))
        return sum(p * w for p, w in zip(recent, weights)) / sum(weights)

    def _ema_pred(self, prices):
        ema5 = Indicators.ema(prices, 5)
        ema10 = Indicators.ema(prices, 10)
        trend = ema5[-1] - ema10[-1]
        return prices[-1] + trend

    def _regression_pred(self, prices):
        n = min(len(prices), 20)
        recent = prices[-n:]
        x = list(range(n))
        slope, intercept = self.linear_regression(x, recent)
        return slope * n + intercept

    def _momentum_pred(self, prices):
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

    def _mean_reversion_pred(self, prices):
        n = min(len(prices), 20)
        recent = prices[-n:]
        mean = sum(recent) / len(recent)
        return prices[-1] + (mean - prices[-1]) * 0.15

    def get_all_predictions(self, prices, current_price):
        """Прогнозы на разные периоды"""

        # Шаг данных ~ 4 часа (OHLC 90 дней = ~540 свечей по 4ч)
        # 1 шаг = ~4 часа
        # 6 шагов = ~24 часа (1 день)
        # 18 шагов = ~3 дня
        # 42 шага = ~7 дней

        pred_1 = self.predict_next(prices, steps=1)    # 4 часа
        pred_6 = self.predict_next(prices, steps=6)    # 1 день
        pred_18 = self.predict_next(prices, steps=18)  # 3 дня
        pred_42 = self.predict_next(prices, steps=42)  # 7 дней

        def calc_change(pred_price):
            if current_price > 0:
                return round(((pred_price - current_price) / current_price) * 100, 4)
            return 0

        def get_direction(change):
            if change > 0.3:
                return "📈 РОСТ"
            elif change < -0.3:
                return "📉 ПАДЕНИЕ"
            return "➡️ БОКОВИК"

        forecasts = {
            "4h": {
                "label": "4 часа",
                "price": pred_1[-1],
                "change_pct": calc_change(pred_1[-1]),
                "direction": get_direction(calc_change(pred_1[-1]))
            },
            "1d": {
                "label": "1 день",
                "price": pred_6[-1],
                "change_pct": calc_change(pred_6[-1]),
                "direction": get_direction(calc_change(pred_6[-1]))
            },
            "3d": {
                "label": "3 дня",
                "price": pred_18[-1],
                "change_pct": calc_change(pred_18[-1]),
                "direction": get_direction(calc_change(pred_18[-1]))
            },
            "7d": {
                "label": "7 дней",
                "price": pred_42[-1],
                "change_pct": calc_change(pred_42[-1]),
                "direction": get_direction(calc_change(pred_42[-1]))
            }
        }

        # Путь цены по дням (для графика)
        path_daily = []
        full_path = self.predict_next(prices, steps=42)
        for i, step in enumerate([0, 5, 11, 17, 23, 29, 35, 41]):
            if step < len(full_path):
                path_daily.append({
                    "day": i,
                    "price": full_path[step]
                })

        return forecasts, path_daily

    def calculate_accuracy(self, prices):
        if len(prices) < 30:
            return {}
        errors = {"ensemble": []}
        for i in range(20, len(prices) - 1):
            subset = prices[:i]
            actual = prices[i]
            pred = self.predict_next(subset, steps=1)
            errors["ensemble"].append(abs(pred[0] - actual))
        metrics = {}
        for name, errs in errors.items():
            if errs:
                mae = sum(errs) / len(errs)
                avg_price = sum(prices[20:]) / len(prices[20:])
                mape = (mae / avg_price) * 100 if avg_price > 0 else 0
                metrics[name] = {
                    "mae": round(mae, 2),
                    "mape": round(mape, 2),
                    "accuracy": round(100 - mape, 2)
                }
        return metrics

    def run(self):
        data, source = self.fetcher.get_data()

        if not data or len(data) < 10:
            return {"error": "Все API временно недоступны. Попробуйте через 2 минуты."}

        closes = [d["close"] for d in data]

        current = self.fetcher.get_current_price()
        current_price = current["price"] if current else closes[-1]

        # Прогнозы на разные периоды
        forecasts, price_path = self.get_all_predictions(closes, current_price)

        # Точность модели
        metrics = self.calculate_accuracy(closes)

        # Главный прогноз (1 день)
        main = forecasts["1d"]

        # Уровни
        recent = closes[-min(30, len(closes)):]
        support = round(min(recent), 2)
        resistance = round(max(recent), 2)

        # Индикаторы и сигналы
        indicators_data, signals = Indicators.analyze(data)

        # Fear & Greed
        fg = self.fetcher.get_fear_greed()

        return {
            "current_price": current_price,
            "current_market": current,
            "forecasts": forecasts,
            "price_path": price_path,
            "main_prediction": main["price"],
            "main_change_pct": main["change_pct"],
            "main_direction": main["direction"],
            "main_period": main["label"],
            "support": support,
            "resistance": resistance,
            "indicators": indicators_data,
            "signals": signals,
            "metrics": metrics,
            "fear_greed": fg,
            "data_points": len(data),
            "data_source": source,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        }
