import numpy as np
import pandas as pd


class Indicators:

    @staticmethod
    def sma(s, p):
        return s.rolling(window=p).mean()

    @staticmethod
    def ema(s, p):
        return s.ewm(span=p, adjust=False).mean()

    @staticmethod
    def rsi(s, p=14):
        d = s.diff()
        g = d.where(d > 0, 0.0)
        l = (-d).where(d < 0, 0.0)
        ag = g.rolling(p).mean()
        al = l.rolling(p).mean()
        rs = ag / al.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(s, fast=12, slow=26, sig=9):
        ef = s.ewm(span=fast, adjust=False).mean()
        es = s.ewm(span=slow, adjust=False).mean()
        m = ef - es
        sl = m.ewm(span=sig, adjust=False).mean()
        return m, sl, m - sl

    @staticmethod
    def bollinger(s, p=20, std=2):
        sma = s.rolling(p).mean()
        st = s.rolling(p).std()
        return sma + st * std, sma, sma - st * std

    @staticmethod
    def stochastic(high, low, close, k=14, d=3):
        ll = low.rolling(k).min()
        hh = high.rolling(k).max()
        k_val = 100 * (close - ll) / (hh - ll)
        return k_val, k_val.rolling(d).mean()

    @staticmethod
    def calculate_all(df):
        r = df.copy()
        col = "close" if "close" in df.columns else "price"
        p = r[col]

        r["sma_7"] = Indicators.sma(p, 7)
        r["sma_14"] = Indicators.sma(p, 14)
        r["sma_30"] = Indicators.sma(p, 30)
        r["ema_7"] = Indicators.ema(p, 7)
        r["ema_14"] = Indicators.ema(p, 14)
        r["ema_30"] = Indicators.ema(p, 30)
        r["rsi_14"] = Indicators.rsi(p)

        m, s, h = Indicators.macd(p)
        r["macd"] = m
        r["macd_signal"] = s
        r["macd_hist"] = h

        bu, bm, bl = Indicators.bollinger(p)
        r["bb_upper"] = bu
        r["bb_mid"] = bm
        r["bb_lower"] = bl
        r["bb_width"] = (bu - bl) / bm
        r["bb_pos"] = (p - bl) / (bu - bl)

        r["mom_5"] = p - p.shift(5)
        r["mom_10"] = p - p.shift(10)
        r["roc_5"] = (p / p.shift(5) - 1) * 100
        r["roc_10"] = (p / p.shift(10) - 1) * 100
        r["vol_7"] = p.pct_change().rolling(7).std() * 100
        r["vol_14"] = p.pct_change().rolling(14).std() * 100
        r["pct_1"] = p.pct_change(1) * 100
        r["pct_3"] = p.pct_change(3) * 100
        r["pct_7"] = p.pct_change(7) * 100

        if all(c in df.columns for c in ["high", "low", "close"]):
            tr1 = df["high"] - df["low"]
            tr2 = abs(df["high"] - df["close"].shift(1))
            tr3 = abs(df["low"] - df["close"].shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            r["atr_14"] = tr.rolling(14).mean()
            sk, sd = Indicators.stochastic(df["high"], df["low"], df["close"])
            r["stoch_k"] = sk
            r["stoch_d"] = sd

        for lag in [1, 2, 3, 5, 7]:
            r[f"lag_{lag}"] = p.shift(lag)
            r[f"pct_lag_{lag}"] = p.pct_change(lag) * 100

        return r

    @staticmethod
    def get_signals(df):
        signals = {}
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        if "rsi_14" in latest.index and not np.isnan(latest["rsi_14"]):
            v = latest["rsi_14"]
            if v < 30:
                signals["RSI"] = {"signal": "BUY", "value": round(v, 1), "reason": "Перепроданность"}
            elif v > 70:
                signals["RSI"] = {"signal": "SELL", "value": round(v, 1), "reason": "Перекупленность"}
            else:
                signals["RSI"] = {"signal": "NEUTRAL", "value": round(v, 1), "reason": "Нейтрально"}

        if "macd" in latest.index and not np.isnan(latest.get("macd", np.nan)):
            if latest["macd"] > latest["macd_signal"] and prev["macd"] <= prev["macd_signal"]:
                signals["MACD"] = {"signal": "BUY", "reason": "Бычье пересечение"}
            elif latest["macd"] < latest["macd_signal"] and prev["macd"] >= prev["macd_signal"]:
                signals["MACD"] = {"signal": "SELL", "reason": "Медвежье пересечение"}
            elif latest["macd"] > latest["macd_signal"]:
                signals["MACD"] = {"signal": "BUY", "reason": "Выше сигнальной"}
            else:
                signals["MACD"] = {"signal": "SELL", "reason": "Ниже сигнальной"}

        if "bb_pos" in latest.index and not np.isnan(latest["bb_pos"]):
            v = latest["bb_pos"]
            if v < 0.05:
                signals["BOLLINGER"] = {"signal": "BUY", "value": round(v, 3), "reason": "У нижней границы"}
            elif v > 0.95:
                signals["BOLLINGER"] = {"signal": "SELL", "value": round(v, 3), "reason": "У верхней границы"}
            else:
                signals["BOLLINGER"] = {"signal": "NEUTRAL", "value": round(v, 3), "reason": "Внутри полос"}

        if "ema_7" in latest.index and not np.isnan(latest["ema_7"]):
            if latest["ema_7"] > latest["ema_30"]:
                signals["EMA_TREND"] = {"signal": "BUY", "reason": "EMA7 > EMA30"}
            else:
                signals["EMA_TREND"] = {"signal": "SELL", "reason": "EMA7 < EMA30"}

        if "mom_5" in latest.index and not np.isnan(latest["mom_5"]):
            v = latest["mom_5"]
            signals["MOMENTUM"] = {
                "signal": "BUY" if v > 0 else "SELL",
                "value": round(v, 2),
                "reason": "Положительный" if v > 0 else "Отрицательный"
            }

        if "stoch_k" in latest.index and not np.isnan(latest.get("stoch_k", np.nan)):
            v = latest["stoch_k"]
            if v < 20:
                signals["STOCHASTIC"] = {"signal": "BUY", "value": round(v, 1), "reason": "Перепроданность"}
            elif v > 80:
                signals["STOCHASTIC"] = {"signal": "SELL", "value": round(v, 1), "reason": "Перекупленность"}
            else:
                signals["STOCHASTIC"] = {"signal": "NEUTRAL", "value": round(v, 1), "reason": "Нейтрально"}

        buy = sum(1 for s in signals.values() if s["signal"] == "BUY")
        sell = sum(1 for s in signals.values() if s["signal"] == "SELL")
        total = len(signals)
        if total > 0:
            if buy / total >= 0.6:
                signals["OVERALL"] = {"signal": "BUY", "confidence": round(buy / total * 100, 1), "reason": f"{buy}/{total} за рост"}
            elif sell / total >= 0.6:
                signals["OVERALL"] = {"signal": "SELL", "confidence": round(sell / total * 100, 1), "reason": f"{sell}/{total} за падение"}
            else:
                signals["OVERALL"] = {"signal": "NEUTRAL", "confidence": 50.0, "reason": "Смешанные сигналы"}

        return signals
