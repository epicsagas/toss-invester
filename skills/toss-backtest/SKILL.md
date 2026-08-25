---
name: toss-backtest
description: >-
 한국 주식 전략 백테스트 스킬. "백테스트해줘", "SMA 크로스 전략 성과 어때", "RSI 반전 전략",
 "삼성전자 SK하이닉스 상관관계" 요청 시 캔들 데이터로 전략 성과 지표와 상관계수를
 계산한다. Strategy backtest (SMA cross / RSI reversion) and pairwise correlation.
---

# toss-backtest — strategy backtest & correlation

Initial cash 10,000,000 KRW, round-trip fees applied on both legs (default
0.2% ≈ KRX 왕복 비용: 수수료 ~0.015% + 매도 세금 ~0.2%; `--fee` to override).

## Two strategies

| Strategy | Rule | Fits |
|----------|------|------|
| `sma_cross` | buy SMA5/20 golden cross, sell dead cross | trending |
| `rsi_reversion` | enter on RSI14 < 30 (buy next bar), exit on RSI14 > 70 | ranging |

## Commands

```bash
# last 200 bars via REST (quick)
python3 scripts/toss.py candles 005930 --interval 1d --count 200 > /tmp/sec.json
# longer history: page with --before (nextBefore cursor from --with-next)
python3 scripts/toss.py candles 005930 --interval 1d --count 200 --with-next
python3 scripts/backtest.py sma_cross --file /tmp/sec.json
python3 scripts/backtest.py rsi_reversion --file /tmp/sec.json --fee 0.0022
python3 scripts/backtest.py correlate /tmp/sec.json /tmp/hynix.json  # pearson + beta
```

Toss has no public full-history archive — REST + `before` 페이지네이션으로
필요한 만큼만 과거를 모은다 (200봉씩).

Metrics: total_return, cagr (252), win_rate, max_drawdown, sharpe,
num_trades, **buy_hold_return (benchmark)**.

## Interpretation rules

- Strategy return < buy_hold ⇒ "worse than simply holding" — state it.
- num_trades ≤ 3 ⇒ sample too small — "statistically weak" warning.
- MDD beyond −20% conflicts with the conservative preset — risk warning.
- Backtests describe the past, not the future. Look-ahead guard: every fill
 happens at the bar AFTER the signal bar (already implemented in the script).
- Prefer ≥ 200 bars of data.
- KRX 특성: 상하한가(±30%)·정리매매·거래정지로 인한 갭은 백테스트에
  반영되지 않는다 — 해석 시 감안.

## Portfolio correlation

Pairs with pearson > 0.8 give no diversification — "effectively the same
asset exposure" warning (동일 업종/테마 종목쌍에서 자주 관찰됨). Beta is
relative volatility (denominator = the second asset's variance) — state
which side is the denominator.
