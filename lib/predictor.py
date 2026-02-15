import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from data_fetcher import DataFetcher
from indicators import Indicators


class XAUTPredictor:

    def __init__(self):
        self.fetcher = DataFetcher()
        self.scaler = StandardScaler()
        self.models = {}
        self.feature_cols = []

    def _get_feature_cols(self, df):
        exclude = {"target", "open", "high", "low", "close", "price", "volume"}
        return [c for c in df.columns if c not in exclude and df[c].dtype in [np.float64, np.int64]]

    def run(self):
        df = self.fetcher.get_xaut_ohlc(days=90)
        if df is None or len(df) < 30:
            df = self.fetcher.get_xaut_history(days=90)
        if df is None or len(df) < 30:
            return {"error": "Недостаточно данных. Попробуйте позже."}

        col = "close" if "close" in df.columns else "price"
        featured = Indicators.calculate_all(df)
        featured["target"] = featured[col].shift(-1)
        featured = featured.dropna()

        if len(featured) < 20:
            return {"error": "Мало данных после обработки"}

        self.feature_cols = self._get_feature_cols(featured)
        X = featured[self.feature_cols].values
        y = featured["target"].values
        X_scaled = self.scaler.fit_transform(X)

        split = int(len(X_scaled) * 0.8)
        X_tr, X_te = X_scaled[:split], X_scaled[split:]
        y_tr, y_te = y[:split], y[split:]

        self.models = {
            "gradient_boosting": GradientBoostingRegressor(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42),
            "random_forest": RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42),
            "linear": LinearRegression()
        }

        metrics = {}
        for name, model in self.models.items():
            model.fit(X_tr, y_tr)
            pred = model.predict(X_te)
            metrics[name] = {"mae": round(mean_absolute_error(y_te, pred), 2)}

        latest = featured[self.feature_cols].iloc[-1:].values
        latest_scaled = self.scaler.transform(latest)

        predictions = {}
        weights = {"gradient_boosting": 0.5, "random_forest": 0.3, "linear": 0.2}
        for name, model in self.models.items():
            predictions[name] = round(model.predict(latest_scaled)[0], 2)

        ensemble = round(sum(predictions[n] * weights[n] for n in predictions), 2)

        current = self.fetcher.get_current_price()
        current_price = current["price"] if current else 0
        change = round(((ensemble - current_price) / current_price) * 100, 4) if current_price > 0 else 0

        if change > 0.3:
            direction = "📈 РОСТ"
        elif change < -0.3:
            direction = "📉 ПАДЕНИЕ"
        else:
            direction = "➡️ БОКОВИК"

        recent = featured[col].tail(30)
        signals = Indicators.get_signals(featured)
        fg = self.fetcher.get_fear_greed()

        return {
            "current_price": current_price,
            "current_market": current,
            "predictions": predictions,
            "ensemble": ensemble,
            "change_pct": change,
            "direction": direction,
            "support": round(recent.min(), 2),
            "resistance": round(recent.max(), 2),
            "signals": signals,
            "metrics": metrics,
            "fear_greed": fg,
            "data_points": len(df),
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        }
