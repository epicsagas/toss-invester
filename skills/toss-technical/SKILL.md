---
name: toss-technical
description: >-
 한국 주식 기술적 지표 분석 스킬. "RSI 어떻게 돼", "MACD 확인해줘", "볼린저 밴드 위치",
 "추세 확인", "지표 분석해줘" 요청 시 지표 계산 + 해석 기준표로 판독한다. Technical
 indicator computation and interpretation against the 8-stage pipeline signal table.
---

# toss-technical — technical indicator analysis

## Computation

```bash
python3 scripts/toss.py candles 005930 --interval 1d --count 200 | python3 scripts/indicators.py
```

Dual timeframe recommended: daily (mid-term trend) + 1m tail (intraday
timing) — Toss candles are 1m/1d only.

## Reading table (8-stage pipeline signal thresholds)

| Indicator | State | Read |
|-----------|-------|------|
| RSI14 | ≥ 70 | overbought — trend strong but extended. Cautious new entries |
| RSI14 | ≤ 30 | oversold — bounce candidate. No knife-catching in downtrends |
| MACD histogram | > 0 rising | upside momentum strengthening |
| MACD histogram | crosses 0 upward | golden cross — buy signal |
| MACD histogram | crosses 0 downward | dead cross — sell signal |
| SMA5 vs SMA20 | crosses up | golden cross |
| SMA5 vs SMA20 | crosses down | death cross |
| price vs SMA20 | above | short-term uptrend |
| Bollinger %B | > 1.0 | upper-band break — extended, band-walk or reversal risk |
| Bollinger %B | < 0.0 | lower-band break — oversold, bounce or downside acceleration |
| Stochastic K vs D | K > D turning up | short-term buy signal |
| ATR14 | — | stop distance = 1.5×ATR by default |
| ADX14 | ≥ 25 | trend has strength — trend strategies apply |
| ADX14 | < 20 | no trend — mean-reversion/stand aside |
| ADX ±DI | +DI > −DI | bullish directional dominance (and vice versa) |
| Williams %R14 | > −20 | overbought (mirror of stochastic) |
| Williams %R14 | < −80 | oversold |
| CCI20 | > +100 | strong upside extension |
| CCI20 | < −100 | strong downside extension |
| disparity (SMA) | > 100 | price above that SMA by (value−100)% |
| trend.read | up/down/sideways | majority (60%) of available directional signals |

**Signals are facts, not advice** — read combinations:
trend up + RSI overbought → "uptrend intact but late entry; wait for a pullback".
trend up + RSI neutral + MACD positive → classic accumulation zone candidate.

## KRX caveats

- 일봉은 수정주가(권리락·액면변경 반영) 기본 — 과거 가격대 해석 시 유의.
- 종목 수급(flow)·공매도와 교차 검증: 지표 상승 + 기관 순매수 = 추세 신뢰 상승,
  지표 상승 + 개인 순매수·공매도 급증 = 분배 의심.

## Output format

Table: indicator/value/state/one-line read. Finish with "Overall: majority
direction + one caveat".
