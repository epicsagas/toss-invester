---
name: toss-portfolio
description: >-
  토스증권 계좌·포트폴리오 점검 스킬. "내 포트폴리오 봐줘", "보유 종목 점검", "수익률 어때",
  "리밸런싱 필요해?" 요청 시 계좌 조회 + 보유별 지표 진단 + 집중도 리스크를 평가한다.
  Account & portfolio review — holdings diagnosis plus concentration risk.
---

# toss-portfolio — account & portfolio review

Keys required (`TOSS_CLIENT_ID`/`TOSS_CLIENT_SECRET`, account header via
`TOSS_ACCOUNT_SEQ` or auto-pick). Read-only — no orders.

## Procedure

1. **Holdings**: `python3 scripts/toss.py holdings`
 — items: symbol/quantity/lastPrice/averagePurchasePrice/profitLoss
 (rate, rateAfterCost)/dailyProfitLoss. Cash: `toss.py buying-power`.
2. **Per-holding diagnosis**: for each held symbol run
 `python3 scripts/toss.py candles <symbol> --interval 1d --count 200 | python3 scripts/indicators.py`
 — price vs avg buy (return), trend, RSI (overbought/oversold), ATR
 (re-derive stop distance). Plus `toss.py flow <symbol>` (수급 이탈 여부).
3. **Concentration analysis**:
   - single symbol weight > max_single (preset default 15%) ⇒ warn
   - total invested weight > max_total (50%) ⇒ warn
   - day PnL / cash ≤ −3% (conservative limit) ⇒ kill-switch warning
     (dailyProfitLoss.amount 합산으로 근사)
4. **Past-decision comparison**:
   `grep '"symbol": "005930"' ~/.toss-investor/decisions.jsonl | tail -3`
   — trajectory vs prior calls: on track, or stop condition reached.
5. **Recommendations**: hold / stop out / partial take-profit / rebalance —
   1-2 lines of rationale each.

## Output format

```markdown
# Portfolio Review (2026-08-26)
## Holdings — table: symbol/name/qty/avg buy/price/return/weight
## Per-holding diagnosis — trend·RSI·stop distance·수급
## Risk — concentration/day PnL/gate status
## Recommendations — hold/act list + reasons
```

## Formulas

- return = (lastPrice − averagePurchasePrice) / averagePurchasePrice;
  valuation = quantity × lastPrice. 원화 손익률은 rateAfterCost(세후) 기준 병기.
- total assets = cash (buying-power KRW) + Σ valuations; weight = valuation / total assets
- recommendations cite numbers; execution goes through toss-trade only
  (user confirmation mandatory).
