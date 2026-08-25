# Eval Report — toss-investor v0.1.0

- Date: 2026-08-26 (KST)
- Scope: plugin at `/Volumes/T5/projects/epicsagas/quant-manager/toss-investor`
- Harness: domain benchmark `benchmarks/eval_runner.py` (live run, `.env` credentials)
- Constraint honored: **read-only endpoints only — no orders, no account/asset
  endpoints called at any point** (prices/candles/orderbook/trades/stocks).
  The order code paths were exercised only by code review and unit
  self-checks, never against the live API.

## Overall: PASS — 1.00

| Dimension | Verdict | Score | Evidence |
|-----------|---------|-------|----------|
| Benchmark (domain) | PASS | 1.0 | composite from 4 subscores below |
| Correctness | PASS | 1.0 | indicator math self-checks + live schema validation |
| Performance | PASS | n/a | avg 149 ms per live read-only endpoint |
| Regression | PASS | — | first run — baseline established (`benchmarks/baselines/BASELINE-20260826T023054.json`) |

## Subscores

| Check | Weight | Result | Detail |
|-------|--------|--------|--------|
| indicator_math | 0.4 | 1.0 | `scripts/test_indicators.py` — trend reads, RSI bounds 0–100, MACD flip, short-series nulls, KRX tick table + candle normalization |
| live_api | 0.3 | 1.0 | prices, 1d/1m candles, orderbook, trades — all 200 OK through `toss.py` (OAuth2 + `{"result"}` unwrap + token cache) |
| indicator_schema | 0.2 | 1.0 | all 8 required fields present on live 삼성전자(005930) daily candles, RSI within [0,100] |
| structure | 0.1 | 1.0 | 7 skills / 7 agents / 5 scripts present, 4 host manifests valid (JSON/YAML/TOML) |

## Performance detail

Live read-only latency per endpoint (first benchmark run, from cold token —
subsequent runs reuse the `~/.toss-investor/token.json` cache):

| Endpoint | Latency |
|----------|---------|
| prices 005930 | 154 ms |
| candles 1d ×200 | 148 ms |
| candles 1m ×200 | 149 ms |
| orderbook 005930 | 139 ms |
| trades ×5 | 153 ms |
| **average** | **149 ms** |

Each invocation is a fresh Python process (~80 ms interpreter startup included).
Within-budget for the 8-stage pipeline (snapshot ≈ 10 read-only calls ≈ 1.5 s).
Rate limits: token-bucket per group (`MARKET_DATA` vs `MARKET_DATA_CHART`
separate) — the wrapper retries once on 429 honoring `Retry-After`.

## Notes & limits

- LLM-as-judge quality rubric: **not run this round** (first baseline is
  deterministic-only). Add in the next eval cycle.
- Order/asset/conditional-order endpoints: untested against live by design —
  coverage via unit asserts (tick snap) + confirm-gate code review only.
- Baseline snapshot: `benchmarks/baselines/latest.json`. Rerun with
  `python3 benchmarks/eval_runner.py full` and compare against it.
