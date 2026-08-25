#!/usr/bin/env python3
"""Backtest indicator strategies on Toss KRX candles + pairwise correlation — stdlib only.

Strategies: sma_cross(5,20), rsi_reversion(14,30/70).
Initial cash 10,000,000 KRW. Metrics: totalReturn, CAGR(252), winRate, MDD,
Sharpe, numTrades. Default fee 0.2% ≈ KRX round-trip (commission ~0.015% +
sell tax 0.15~0.2%); override with --fee.

Usage:
 toss.py candles 005930 --interval 1d --count 200 | backtest.py sma_cross
 toss.py candles 005930 --interval 1d --count 200 | backtest.py rsi_reversion
 toss.py candles 005930 --interval 1d --count 200 > a.json
 toss.py candles 000660 --interval 1d --count 200 > b.json
 backtest.py correlate a.json b.json
"""
import json
import math
import sys


def load(path=None):
    return json.load(open(path) if path else sys.stdin)


def closes(candles):
    return [float(c["trade_price"]) for c in candles]


def sma_series(v, n):
    return [None] * (n - 1) + [sum(v[i - n + 1:i + 1]) / n for i in range(n - 1, len(v))]


def rsi_series(v, n=14):
    out = [None] * n
    gain = loss = 0.0
    for i in range(1, n + 1):
        d = v[i] - v[i - 1]
        gain += max(d, 0); loss += max(-d, 0)
        out.append(100.0 if loss == 0 else 100 - 100 / (1 + (gain / n) / (loss / n)))
    for i in range(n + 1, len(v)):
        d = v[i] - v[i - 1]
        gain = (gain * (n - 1) + max(d, 0)) / n
        loss = (loss * (n - 1) + max(-d, 0)) / n
        out.append(100.0 if loss == 0 else 100 - 100 / (1 + (gain / n) / (loss / n)))
    return out


def backtest(candles, strategy, fee=0.002):
    v = closes(candles)
    cash, coins, entry, trades = 10_000_000.0, 0.0, 0.0, []
    if strategy == "sma_cross":
        fast, slow = sma_series(v, 5), sma_series(v, 20)
        for i in range(21, len(v)):
            prev_bull = fast[i - 1] and slow[i - 1] and fast[i - 1] > slow[i - 1]
            bull = fast[i] and slow[i] and fast[i] > slow[i]
            if bull and not prev_bull and coins == 0:
                coins = cash * (1 - fee) / v[i]; entry = v[i]; cash = 0.0
            elif not bull and prev_bull and coins > 0:
                cash = coins * v[i] * (1 - fee); trades.append(v[i] / entry - 1); coins = 0.0
    elif strategy == "rsi_reversion":
        r = rsi_series(v, 14)
        for i in range(15, len(v)):
            if r[i - 1] is not None:
                if r[i - 1] < 30 and coins == 0:  # entered oversold → buy next bar
                    coins = cash * (1 - fee) / v[i]; entry = v[i]; cash = 0.0
                elif r[i - 1] > 70 and coins > 0:  # left overbought → sell
                    cash = coins * v[i] * (1 - fee); trades.append(v[i] / entry - 1); coins = 0.0
    else:
        raise SystemExit(f"unknown strategy: {strategy}")

    final = cash + coins * v[-1]
    total_ret = final / 10_000_000 - 1
    days = len(v)
    cagr = (final / 10_000_000) ** (252 / days) - 1 if days > 0 else 0
    wins = [t for t in trades if t > 0]
    win_rate = len(wins) / len(trades) if trades else 0.0

    # MDD + Sharpe on daily equity marks
    peak, mdd = 10_000_000.0, 0.0
    equity = []
    for i, price in enumerate(v):
        eq = cash + coins * price if i >= 21 else 10_000_000.0
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
        equity.append(eq)
    rets = [equity[i] / equity[i - 1] - 1 for i in range(1, len(equity)) if equity[i - 1] > 0]
    mean = sum(rets) / len(rets) if rets else 0
    std = math.sqrt(sum((x - mean) ** 2 for x in rets) / len(rets)) if rets else 0
    sharpe = mean / std * math.sqrt(252) if std > 0 else 0

    return {"strategy": strategy, "market": candles[-1]["market"], "bars": days,
            "initial_krw": 10_000_000, "final_krw": round(final),
            "fee_rate": fee,
            "total_return_pct": round(total_ret * 100, 2),
            "cagr_pct": round(cagr * 100, 2),
            "num_trades": len(trades), "win_rate_pct": round(win_rate * 100, 1),
            "max_drawdown_pct": round(mdd * 100, 2), "sharpe": round(sharpe, 2),
            "buy_hold_return_pct": round((v[-1] / v[0] - 1) * 100, 2)}


def correlate(a, b):
    va, vb = closes(a), closes(b)
    n = min(len(va), len(vb))
    va, vb = va[-n:], vb[-n:]
    ma, mb = sum(va) / n, sum(vb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(va, vb))
    var_a = sum((x - ma) ** 2 for x in va)
    var_b = sum((y - mb) ** 2 for y in vb)
    pearson = cov / math.sqrt(var_a * var_b) if var_a > 0 and var_b > 0 else 0
    # beta vs b as "market": cov / var_b
    beta = cov / var_b if var_b > 0 else 0
    return {"pair": f"{a[-1]['market']}/{b[-1]['market']}", "bars": n,
            "pearson": round(pearson, 3), "beta": round(beta, 3)}


def main():
    import argparse
    p = argparse.ArgumentParser(description="Toss KRX backtest + correlation")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sma_cross"); s.add_argument("--file", default=None); s.add_argument("--fee", type=float, default=0.002)
    s = sub.add_parser("rsi_reversion"); s.add_argument("--file", default=None); s.add_argument("--fee", type=float, default=0.002)
    s = sub.add_parser("correlate"); s.add_argument("a"); s.add_argument("b")
    a = p.parse_args()
    if a.cmd == "correlate":
        print(json.dumps(correlate(load(a.a), load(a.b)), ensure_ascii=False))
    else:
        print(json.dumps(backtest(load(a.file), a.cmd, a.fee), ensure_ascii=False))


if __name__ == "__main__":
    main()
