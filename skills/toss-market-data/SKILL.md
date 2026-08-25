---
name: toss-market-data
description: >-
  한국 주식 시장 데이터 수집 스킬. "지금 삼성전자 시세", "호가 보여줘", "캔들 데이터",
  "거래대금 높은 종목", "코스피 지수", "외국인 순매수", "환율" 요청 시 시세/호가/캔들/
  체결/수급/지수 데이터를 수집해 정리한다. 분석 없이 데이터 팩트만 제공. KRX market
  data collection — price/orderbook/candles/수급 facts without analysis.
---

# toss-market-data — market data collection

Needs `TOSS_CLIENT_ID`/`TOSS_CLIENT_SECRET` (every Toss call is keyed —
unlike Upbit there are no keyless public endpoints). All commands run from
the plugin root `scripts/`.

## Commands

| Purpose | Command |
|---------|---------|
| Price(s) | `python3 scripts/toss.py prices 005930 [000660,...]` (≤200) |
| Stock info | `python3 scripts/toss.py stocks 005930` — name/market(코스피·코스닥)/status |
| Daily 200 | `python3 scripts/toss.py candles 005930 --interval 1d --count 200` (oldest-first, 수정주가) |
| Minute candles | `python3 scripts/toss.py candles 005930 --interval 1m --count 200` — Toss has 1m/1d only |
| Order book | `python3 scripts/toss.py orderbook 005930` — asks/bids |
| Recent trades | `python3 scripts/toss.py trades 005930 --count 50` |
| 상한가/하한가 | `python3 scripts/toss.py price-limits 005930` |
| Warnings | `python3 scripts/toss.py warnings 005930` — 투자유의/VI/과열/정리매매 |
| 종목 수급 | `python3 scripts/toss.py flow 005930` — 투자자별 순매수·외국인 보유율 |
| 공매도 | `python3 scripts/toss.py short-selling 005930` |
| Index | `python3 scripts/toss.py index prices KOSPI,KOSDAQ` (+ `index candles`) |
| 시장 수급 | `python3 scripts/toss.py market-flow KOSPI --interval 1d` |
| 환율 | `python3 scripts/toss.py exchange-rate --base USD --quote KRW` |
| 장 캘린더 | `python3 scripts/toss.py market-calendar` — 정규 09:00–15:30 KST, 휴장일 |

## Interpretation guide

- **Supply balance**: 매수호가 잔량 합 > 매도호가 잔량 합 means bid-side
  dominance — not a standalone signal (허호가 possible). Cross-check with
  trades.
- **수급**: `flow` netBuyVolume of 외국인/기관 = institutional demand.
  당일 `individual`/기관 세부는 장중 null (잠정치 미제공) — evening 확정치 기준.
  `foreigner` here is 등록외국인 (시장 지표 `market-flow`의 외국인과 기준 다름).
- **공매도**: shortSellingVolumeRate는 당일 거래량 대비 비중 (소수 비율 —
  0.03 = 3%). 최근 5일 평균 대비 급증 여부가 곰 논거.
- **Flash move**: |당일 등락| > 5% ⇒ flag "급등락" in the snapshot.
- 수치 필드는 전부 문자열로 내려온다 — 보고 시에만 포맷.

## Output format

A table (symbol/name/price/change/volume). For candle requests, report key
stats (last 5 bars OHLCV) instead of the full JSON; save the raw JSON to a
file and give the path.
