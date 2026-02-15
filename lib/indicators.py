import math


class Indicators:

    @staticmethod
    def sma(prices, period):
        result = []
        for i in range(len(prices)):
            if i < period - 1:
                result.append(None)
            else:
                result.append(sum(prices[i-period+1:i+1]) / period)
        return result

    @staticmethod
    def ema(prices, period):
        result = []
        k = 2 / (period + 1)
        for i in range(len(prices)):
            if i == 0:
                result.append(prices[0])
            else:
                result.append(prices[i] * k + result[-1] * (1 - k))
        return result

    @staticmethod
    def rsi(prices, period=14):
        result = [None] * period
        for i in range(period, len(prices)):
            gains, losses = [], []
            for j in range(i - period + 1, i + 1):
                diff = prices[j] - prices[j-1]
                gains.append(diff if diff > 0 else 0)
                losses.append(-diff if diff < 0 else 0)
            avg_gain = sum(gains) / period
            avg_loss = sum(losses) / period
            if avg_loss == 0:
                result.append(100)
            else:
                rs = avg_gain / avg_loss
                result.append(100 - (100 / (1 + rs)))
        return result

    @staticmethod
    def macd(prices, fast=12, slow=26, sig=9):
        ema_f = Indicators.ema(prices, fast)
        ema_s = Indicators.ema(prices, slow)
        macd_line = [f - s for f, s in zip(ema_f, ema_s)]
        signal_line = Indicators.ema(macd_line, sig)
        histogram = [m - s for m, s in zip(macd_line, signal_line)]
        return macd_line, signal_line, histogram

    @staticmethod
    def bollinger(prices, period=20, num_std=2):
        upper, mid, lower = [], [], []
        for i in range(len(prices)):
            if i < period - 1:
                upper.append(None)
                mid.append(None)
                lower.append(None)
            else:
                window = prices[i-period+1:i+1]
                m = sum(window) / period
                variance = sum((x - m) ** 2 for x in window) / period
                std = math.sqrt(variance)
                mid.append(m)
                upper.append(m + std * num_std)
                lower.append(m - std * num_std)
        return upper, mid, lower

    @staticmethod
    def momentum(prices, period=5):
        result = [None] * period
        for i in range(period, len(prices)):
            result.append(prices[i] - prices[i - period])
        return result

    @staticmethod
    def roc(prices, period=5):
        result = [None] * period
        for i in range(period, len(prices)):
            if prices[i - period] != 0:
                result.append(((prices[i] / prices[i - period]) - 1) * 100)
            else:
                result.append(0)
        return result

    @staticmethod
    def stochastic(highs, lows, closes, k_period=14, d_period=3):
        k_vals = [None] * (k_period - 1)
        for i in range(k_period - 1, len(closes)):
            h = max(highs[i-k_period+1:i+1])
            l = min(lows[i-k_period+1:i+1])
            if h - l == 0:
                k_vals.append(50)
            else:
                k_vals.append(100 * (closes[i] - l) / (h - l))

        valid_k = [v for v in k_vals if v is not None]
        d_vals = [None] * (len(k_vals) - len(valid_k))
        d_vals += Indicators.sma(valid_k, d_period)
        return k_vals, d_vals

    @staticmethod
    def volatility(prices, period=7):
        result = [None] * period
        for i in range(period, len(prices)):
            returns = []
            for j in range(i - period + 1, i + 1):
                if prices[j-1] != 0:
                    returns.append((prices[j] - prices[j-1]) / prices[j-1])
            if returns:
                mean_r = sum(returns) / len(returns)
                var = sum((r - mean_r) ** 2 for r in returns) / len(returns)
                result.append(math.sqrt(var) * 100)
            else:
                result.append(0)
        return result

    @staticmethod
    def analyze(data):
        closes = [d["close"] for d in data]
        highs = [d.get("high", d["close"]) for d in data]
        lows = [d.get("low", d["close"]) for d in data]

        n = len(closes)
        if n < 30:
            return None, {}

        rsi = Indicators.rsi(closes)
        macd_line, macd_sig, macd_hist = Indicators.macd(closes)
        bb_upper, bb_mid, bb_lower = Indicators.bollinger(closes)
        ema7 = Indicators.ema(closes, 7)
        ema14 = Indicators.ema(closes, 14)
        ema30 = Indicators.ema(closes, 30)
        mom5 = Indicators.momentum(closes, 5)
        roc5 = Indicators.roc(closes, 5)
        vol7 = Indicators.volatility(closes, 7)
        stoch_k, stoch_d = Indicators.stochastic(highs, lows, closes)

        indicators = {
            "rsi_14": rsi[-1] if rsi[-1] is not None else None,
            "macd": macd_line[-1],
            "macd_signal": macd_sig[-1],
            "macd_hist": macd_hist[-1],
            "bb_upper": bb_upper[-1],
            "bb_mid": bb_mid[-1],
            "bb_lower": bb_lower[-1],
            "bb_pos": None,
            "ema_7": ema7[-1],
            "ema_14": ema14[-1],
            "ema_30": ema30[-1],
            "momentum_5": mom5[-1],
            "roc_5": roc5[-1],
            "volatility_7": vol7[-1],
            "stoch_k": stoch_k[-1],
            "stoch_d": stoch_d[-1] if stoch_d[-1] is not None else None,
        }

        if bb_upper[-1] is not None and bb_lower[-1] is not None:
            span = bb_upper[-1] - bb_lower[-1]
            if span > 0:
                indicators["bb_pos"] = (closes[-1] - bb_lower[-1]) / span

        return indicators, Indicators.get_signals(indicators, closes, rsi, macd_line, macd_sig)

    @staticmethod
    def get_signals(ind, closes, rsi_list, macd_list, macd_sig_list):
        signals = {}

        # RSI
        rsi = ind.get("rsi_14")
        if rsi is not None:
            if rsi < 30:
                signals["RSI"] = {"signal": "BUY", "value": round(rsi, 1), "reason": "Перепроданность"}
            elif rsi > 70:
                signals["RSI"] = {"signal": "SELL", "value": round(rsi, 1), "reason": "Перекупленность"}
            else:
                signals["RSI"] = {"signal": "NEUTRAL", "value": round(rsi, 1), "reason": "Нейтрально"}

        # MACD
        if len(macd_list) >= 2 and len(macd_sig_list) >= 2:
            if macd_list[-1] > macd_sig_list[-1] and macd_list[-2] <= macd_sig_list[-2]:
                signals["MACD"] = {"signal": "BUY", "reason": "Бычье пересечение"}
            elif macd_list[-1] < macd_sig_list[-1] and macd_list[-2] >= macd_sig_list[-2]:
                signals["MACD"] = {"signal": "SELL", "reason": "Медвежье пересечение"}
            elif macd_list[-1] > macd_sig_list[-1]:
                signals["MACD"] = {"signal": "BUY", "reason": "Выше сигнальной"}
            else:
                signals["MACD"] = {"signal": "SELL", "reason": "Ниже сигнальной"}

        # Bollinger
        bb_pos = ind.get("bb_pos")
        if bb_pos is not None:
            if bb_pos < 0.05:
                signals["BOLLINGER"] = {"signal": "BUY", "value": round(bb_pos, 3), "reason": "У нижней границы"}
            elif bb_pos > 0.95:
                signals["BOLLINGER"] = {"signal": "SELL", "value": round(bb_pos, 3), "reason": "У верхней границы"}
            else:
                signals["BOLLINGER"] = {"signal": "NEUTRAL", "value": round(bb_pos, 3), "reason": "Внутри полос"}

        # EMA
        ema7 = ind.get("ema_7")
        ema30 = ind.get("ema_30")
        if ema7 is not None and ema30 is not None:
            if ema7 > ema30:
                signals["EMA_TREND"] = {"signal": "BUY", "reason": "EMA7 > EMA30"}
            else:
                signals["EMA_TREND"] = {"signal": "SELL", "reason": "EMA7 < EMA30"}

        # Momentum
        mom = ind.get("momentum_5")
        if mom is not None:
            signals["MOMENTUM"] = {
                "signal": "BUY" if mom > 0 else "SELL",
                "value": round(mom, 2),
                "reason": "Положительный" if mom > 0 else "Отрицательный"
            }

        # Stochastic
        sk = ind.get("stoch_k")
        if sk is not None:
            if sk < 20:
                signals["STOCHASTIC"] = {"signal": "BUY", "value": round(sk, 1), "reason": "Перепроданность"}
            elif sk > 80:
                signals["STOCHASTIC"] = {"signal": "SELL", "value": round(sk, 1), "reason": "Перекупленность"}
            else:
                signals["STOCHASTIC"] = {"signal": "NEUTRAL", "value": round(sk, 1), "reason": "Нейтрально"}

        # Overall
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
