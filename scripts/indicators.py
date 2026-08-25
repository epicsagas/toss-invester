#!/usr/bin/env python3
"""Technical indicators over Toss KRX candles — stdlib only.

Input: candles JSON array (oldest first) from toss.py candles, via stdin or --file.
Output: JSON with latest indicator values and a machine-readable trend summary.

Usage:
  toss.py candles 005930 --interval 1d --count 200 | indicators.py
  indicators.py --file candles.json --sma 20,60 --rsi 14 --macd 12,26,9 --bb 20,2 --atr 14
"""
import argparse
import json
import sys


def sma(v, n):
    if len(v) < n:
        return None
    return sum(v[-n:]) / n


def ema_series(v, n):
    if len(v) < n:
        return []
    k = 2 / (n + 1)
    e = [sum(v[:n]) / n]
    for x in v[n:]:
        e.append(x * k + e[-1] * (1 - k))
    return e


def rsi(v, n=14):
    if len(v) < n + 1:
        return None
    gains, losses = 0.0, 0.0
    for i in range(-n, 0):
        d = v[i] - v[i - 1]
        gains += max(d, 0); losses += max(-d, 0)
    if losses == 0:
        return 100.0
    rs = (gains / n) / (losses / n)
    return 100 - 100 / (1 + rs)


def macd(v, fast=12, slow=26, sig=9):
    if len(v) < slow + sig:
        return None
    ef, es = ema_series(v, fast), ema_series(v, slow)
    line = [a - b for a, b in zip(ef[len(ef) - len(es):], es)] if len(es) else []
    if len(line) < sig:
        return None
    sig_series = ema_series(line, sig)
    m, s = line[-1], sig_series[-1]
    prev_m, prev_s = line[-2], sig_series[-2]
    return {"macd": round(m, 4), "signal": round(s, 4),
            "histogram": round(m - s, 4), "cross": "bullish" if prev_m <= prev_s and m > s else
                        "bearish" if prev_m >= prev_s and m < s else "none"}


def bollinger(v, n=20, k=2.0):
    m = sma(v, n)
    if m is None:
        return None
    var = sum((x - m) ** 2 for x in v[-n:]) / n
    sd = var ** 0.5
    price = v[-1]
    return {"mid": round(m, 4), "upper": round(m + k * sd, 4), "lower": round(m - k * sd, 4),
            "percent_b": round((price - (m - k * sd)) / (2 * k * sd), 4) if sd > 0 else 0.5}


def atr(candles, n=14):
    if len(candles) < n + 1:
        return None
    trs = []
    for i in range(-n, 0):
        c = candles[i]; p = candles[i - 1]
        trs.append(max(c["high_price"] - c["low_price"],
                       abs(c["high_price"] - p["trade_price"]),
                       abs(c["low_price"] - p["trade_price"])))
    return round(sum(trs) / n, 6)


def stochastic(candles, n=14, k_smooth=3, d_smooth=3):
    if len(candles) < n + k_smooth + d_smooth:
        return None
    def raw_k(i):
        window = candles[i - n + 1:i + 1]
        hh = max(float(c["high_price"]) for c in window)
        ll = min(float(c["low_price"]) for c in window)
        return 50.0 if hh == ll else (float(candles[i]["trade_price"]) - ll) / (hh - ll) * 100
    ks = [raw_k(i) for i in range(len(candles) - k_smooth - d_smooth + 1, len(candles))]
    k_line = [sum(ks[i - k_smooth + 1:i + 1]) / k_smooth for i in range(k_smooth - 1, len(ks))]
    if len(k_line) < d_smooth:
        return None
    k_val = k_line[-1]
    d_val = sum(k_line[-d_smooth:]) / d_smooth
    return {"k": round(k_val, 2), "d": round(d_val, 2)}


def vwap(candles):
    if not candles:
        return None
    tpv = sum((float(c["trade_price"]) * 3 + float(c["high_price"]) + float(c["low_price"])) / 5 * float(c["volume"]) for c in candles)
    vv = sum(float(c["volume"]) for c in candles)
    return round(tpv / vv, 4) if vv > 0 else None


def obv(candles):
    total, prev = 0.0, None
    for c in candles:
        price = float(c["trade_price"])
        vol = float(c["volume"])
        if prev is not None:
            total += vol if price > prev else -vol if price < prev else 0
        prev = price
    return round(total, 2)


def adx(candles, n=14):
    """Wilder ADX — trend strength, direction-agnostic."""
    if len(candles) < 2 * n:
        return None
    trs, pdms, mdms = [], [], []
    for i in range(1, len(candles)):
        c, p = candles[i], candles[i - 1]
        ch, cl, ph, pl = (float(c["high_price"]), float(c["low_price"]),
                          float(p["high_price"]), float(p["low_price"]))
        pc = float(p["trade_price"])
        trs.append(max(ch - cl, abs(ch - pc), abs(cl - pc)))
        up = ch - ph
        down = pl - cl
        pdms.append(up if up > down and up > 0 else 0.0)
        mdms.append(down if down > up and down > 0 else 0.0)
    atr = sum(trs[:n]) / n
    pdm_s = sum(pdms[:n]) / n
    mdm_s = sum(mdms[:n]) / n
    pdi = 100 * pdm_s / atr if atr > 0 else 0.0
    mdi = 100 * mdm_s / atr if atr > 0 else 0.0
    dxs = []
    for i in range(n, len(trs)):  # Wilder-smooth over the tail
        atr = (atr * (n - 1) + trs[i]) / n
        pdm_s = (pdm_s * (n - 1) + pdms[i]) / n
        mdm_s = (mdm_s * (n - 1) + mdms[i]) / n
        pdi = 100 * pdm_s / atr if atr > 0 else 0.0
        mdi = 100 * mdm_s / atr if atr > 0 else 0.0
        if pdi + mdi > 0:
            dxs.append(100 * abs(pdi - mdi) / (pdi + mdi))
    if not dxs:
        return None
    adx_val = sum(dxs[-n:]) / min(n, len(dxs))
    return {"adx": round(adx_val, 2), "plus_di": round(pdi, 2), "minus_di": round(mdi, 2)}


def williams_r(candles, n=14):
    if len(candles) < n:
        return None
    window = candles[-n:]
    hh = max(float(c["high_price"]) for c in window)
    ll = min(float(c["low_price"]) for c in window)
    price = float(candles[-1]["trade_price"])
    if hh == ll:
        return -50.0
    return round((hh - price) / (hh - ll) * -100, 2)


def cci(candles, n=20):
    if len(candles) < n:
        return None
    tps = [(float(c["high_price"]) + float(c["low_price"]) + float(c["trade_price"])) / 3 for c in candles]
    ma = sum(tps[-n:]) / n
    mean_dev = sum(abs(t - ma) for t in tps[-n:]) / n
    if mean_dev == 0:
        return 0.0
    return round((tps[-1] - ma) / (0.015 * mean_dev), 2)


def main():
    p = argparse.ArgumentParser(description="Toss KRX technical indicators")
    p.add_argument("--file", default=None, help="candles JSON file (default stdin)")
    p.add_argument("--sma", default="20,60", help="comma-separated periods")
    p.add_argument("--ema", default="12,26")
    p.add_argument("--rsi", type=int, default=14)
    p.add_argument("--macd", default="12,26,9")
    p.add_argument("--bb", default="20,2")
    p.add_argument("--atr", type=int, default=14)
    args = p.parse_args()

    candles = json.load(open(args.file) if args.file else sys.stdin)
    closes = [float(c["trade_price"]) for c in candles]
    price = closes[-1]

    out = {"market": candles[-1]["market"], "price": price,
           "date": candles[-1].get("candle_date_kst") or candles[-1].get("candle_date_time_utc")}
    out["sma"] = {n: sma(closes, int(n)) for n in args.sma.split(",")}
    out["ema"] = {n: (ema_series(closes, int(n)) or [None])[-1] for n in args.ema.split(",")}
    out["rsi"] = rsi(closes, args.rsi)
    f, s, g = (int(x) for x in args.macd.split(","))
    out["macd"] = macd(closes, f, s, g)
    bn, bk = (float(x) for x in args.bb.split(","))
    out["bollinger"] = bollinger(closes, int(bn), bk)
    out["atr"] = atr(candles, args.atr)
    out["stochastic"] = stochastic(candles)
    out["vwap"] = vwap(candles)
    out["obv"] = obv(candles)
    out["adx"] = adx(candles)
    out["williams_r"] = williams_r(candles)
    out["cci"] = cci(candles)
    out["disparity"] = {n: round(price / m * 100, 2) for n, m in out["sma"].items() if m}

    # returns for momentum context
    def ret(n):
        return round((price / closes[-1 - n] - 1) * 100, 2) if len(closes) > n else None
    out["returns_pct"] = {"1": ret(1), "7": ret(7), "30": ret(30)}

    # machine-readable trend summary — majority of available directional signals.
    # RSI is deliberately excluded (overbought/oversold is an overlay, not direction).
    score, avail = 0, 0
    def vote(cond):
        nonlocal score, avail
        avail += 1
        score += 1 if cond else -1
    sma20, sma60 = out["sma"].get("20"), out["sma"].get("60")
    if sma20 and sma60:
        vote(sma20 > sma60)
        vote(price > sma60)
    if sma20:
        vote(price > sma20)
    if out["macd"]:
        vote(out["macd"]["histogram"] > 0)
        if out["macd"]["cross"] in ("bullish", "bearish"):
            vote(out["macd"]["cross"] == "bullish")
    if out["stochastic"]:
        k, d = out["stochastic"]["k"], out["stochastic"]["d"]
        if k != d:
            vote(k > d)
    import math
    need = math.ceil(avail * 0.6) if avail else 0
    out["trend"] = {"score": score, "of": avail,
                    "read": "up" if score >= need else "down" if score <= -need else "sideways"}

    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
