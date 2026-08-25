#!/usr/bin/env python3
"""Self-check for indicators math + toss.py helpers — python3 test_indicators.py, exit 0 = pass."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from toss import tick_size, snap_to_tick, normalize_candle  # noqa: E402


def run(candles):
    p = subprocess.run([sys.executable, str(HERE / "indicators.py")], input=json.dumps(candles),
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def candle(price, vol=1.0, high=None, low=None):
    return {"market": "005930", "trade_price": price, "high_price": high or price,
            "low_price": low or price, "volume": vol,
            "candle_date_time_utc": "2026-01-01T00:00:00+09:00"}


# accelerating uptrend — all 4 directional signals up
prices = [1000 + i * i * 0.5 for i in range(1, 71)]
rising = [candle(p, vol=i) for i, p in enumerate(prices, 1)]
out = run(rising)
assert out["trend"]["read"] == "up", out["trend"]
assert out["rsi"] == 100.0          # pure gains
assert out["sma"]["20"] == sum(prices[50:]) / 20
assert out["bollinger"]["percent_b"] > 0.9  # price at top of band
assert out["returns_pct"]["1"] == round((prices[-1] / prices[-2] - 1) * 100, 2)

# accelerating downtrend — all 4 directional signals down
prices = [1000 - i * i for i in range(1, 71)]
falling = [candle(p) for p in prices]
out = run(falling)
assert out["trend"]["read"] == "down", out["trend"]
assert out["rsi"] == 0.0            # pure losses

# flat then jump: macd histogram flips positive
flat_then_jump = [candle(100) for _ in range(40)] + [candle(110), candle(115), candle(120)]
out = run(flat_then_jump)
assert out["macd"]["histogram"] > 0
assert out["price"] == 120

# new indicators: bounds and direction
out = run(rising)
assert -100 <= out["williams_r"] <= 0 and out["williams_r"] > -20  # at highs
assert out["cci"] > 0
assert out["adx"] is not None and out["adx"]["plus_di"] > out["adx"]["minus_di"]
assert out["disparity"]["20"] > 100

# too few candles must not crash, nulls instead
short = [candle(10), candle(11)]
out = run(short)
assert out["sma"]["20"] is None and out["macd"] is None and out["adx"] is None

# toss.py helpers — KRX tick table + candle normalization
assert tick_size(1500) == 1 and tick_size(4999) == 5 and tick_size(19999) == 10
assert tick_size(49999) == 50 and tick_size(199999) == 100 and tick_size(499999) == 500
assert tick_size(500000) == 1000 and tick_size(5_000_000) == 1000
assert snap_to_tick(4999) == 4995 and snap_to_tick(73500) == 73500
assert snap_to_tick(73550) == 73500  # floors, never rounds up
norm = normalize_candle("005930", {"timestamp": "2026-08-26T09:00:00+09:00",
                                   "openPrice": "71600", "highPrice": "72300",
                                   "lowPrice": "71500", "closePrice": "72000",
                                   "volume": "3521000", "currency": "KRW"})
assert norm == {"market": "005930", "candle_date_time_utc": "2026-08-26T09:00:00+09:00",
                "opening_price": 71600.0, "high_price": 72300.0, "low_price": 71500.0,
                "trade_price": 72000.0, "volume": 3521000.0}, norm

print("all indicator self-checks passed")
