---
name: toss-analyze
description: >-
 한국 주식(KRX) 투자 종합 분석·의사결정 오케스트레이터. "삼성전자 분석해줘", "005930 사도 될까",
 "포트폴리오 점검", "매매 신호 봐줘", "이 종목 판단해줘" 요청 시 8단계 멀티 역할 분석 파이프라인
 (스냅샷 → 시장분석 → 불/곰 디비트 2라운드 → 리서치 매니저 판정 → 리스크 게이트 →
 포트폴리오 판단 → 트레이더 제안)으로 최종 투자 보고서를 낸다. TradingAgents 스타일
 딥 애널리시스 FSM 포팅. Full KRX stock investment decision orchestrator — 8-stage
 multi-role pipeline producing a final report.
---

# toss-analyze — 8-stage pipeline orchestrator

Runs the TradingAgents-style 8-stage hierarchical debate pipeline on KRX stocks
(코스피/코스닥) via the Toss Open API. Hierarchical judge structure — no
voting; each stage's verdict is inherited by the next.

## Absolute rules

1. **Never place a real order without explicit user confirmation.** Analysis
 and proposal stages never call order APIs. Execution is delegated to the
 toss-trade skill.
2. EVERY Toss call (시세 포함) needs `TOSS_CLIENT_ID`/`TOSS_CLIENT_SECRET`.
 Account/asset/order calls additionally need `TOSS_ACCOUNT_SEQ` (auto-picked
 from the first BROKERAGE account when unset). Without keys: explain and stop.
3. All scripts are stdlib-only Python under the plugin root `scripts/`.
4. 분석 종목은 앵커로 고정 (환각 방지): "분석 대상: {종목명} (종목코드 {symbol}, {시장})".

## Tooling

| Step | Command |
|------|---------|
| Name lookup | `python3 scripts/toss.py stocks 005930` — name/market/status |
| Price | `python3 scripts/toss.py prices 005930` |
| Daily candles | `python3 scripts/toss.py candles 005930 --interval 1d --count 200` (oldest-first) |
| Intraday | `python3 scripts/toss.py candles 005930 --interval 1m --count 200` |
| Indicators | `python3 scripts/toss.py candles 005930 --interval 1d --count 200 \| python3 scripts/indicators.py` |
| Orderbook | `python3 scripts/toss.py orderbook 005930` |
| 상한가/하한가 | `python3 scripts/toss.py price-limits 005930` |
| Warnings | `python3 scripts/toss.py warnings 005930` |
| 종목 수급 | `python3 scripts/toss.py flow 005930` |
| 공매도 | `python3 scripts/toss.py short-selling 005930` |
| Index | `python3 scripts/toss.py index prices KOSPI,KOSDAQ` |
| 시장 수급 | `python3 scripts/toss.py market-flow KOSPI --interval 1d` |
| Holdings (keys) | `python3 scripts/toss.py holdings` / `buying-power` |
| Screening | `toss-screen` skill |

## 8-stage pipeline

Full per-stage prompts live in `references/pipeline.md`. Summary:

1. **Snapshot** — daily 200 + 1m 200 candles, prices, orderbook,
 price-limits, warnings, indicators, 종목 수급(투자자별 순매수·외국인 보유율),
 공매도, KOSPI/KOSDAQ 지표, journal recall 3 (`~/.toss-investor/decisions.jsonl`),
 news/공시 3-5 via web tools (optional).
2. **Market analyst (quick)** — 3-4 Korean sentences: trend/volatility/
 volume anomaly/indicator read + 수급 한 줄.
3. **Bull vs Bear round 1** — 2-3 independent Korean sentences each, every
 number cited from the snapshot (수급·공매도 데이터는 강세/약세 논거의 직접 재료).
4. **Round 2 (rebuttal)** — directly attack the opponent's round-1 arguments.
5. **Research manager verdict** — 5-tier JSON judging the debate:
 `{"rating": "Buy|Overweight|Hold|Underweight|Sell", "confidence", "debate_winner",
 "key_thesis", "catalysts", "risks", "price_target", "time_horizon"}`
6. **Risk manager overlay** — 6-gate pass/fail + position sizing
 (`floor(buying_power × pct/100 ÷ entry)` shares). See `references/risk-gates.md`.
7. **Portfolio manager decision** — past-decision recall injected (grep the
 symbol's prior entries in `~/.toss-investor/decisions.jsonl`), then final
 override: enter / wait / exit.
8. **Trader proposal** — order plan JSON: market/limit, entry (tick-snapped,
 inside 상한가/하한가), quantity (integer shares), stop-loss (entry − 1.5×ATR14).
 **Proposal only — execution requires user confirmation via the toss-trade skill.**

## Output format (final report)

```markdown
# 삼성전자(005930) Investment Analysis (2026-08-26)
## Snapshot — price/trend/수급/공매도 key numbers + warnings 상태
## Market analysis — 3-4 sentences
## Bull vs Bear — round-1 arguments + round-2 rebuttal gist
## Research manager verdict — rating/confidence/price_target
## Risk — gate results + proposed position size
## Portfolio decision — final call with past-decision recall
## Trader proposal — order JSON + stop/target rationale
## Conclusion — one paragraph: buy / wait / sell + top 3 reasons
```

After the verdict, append one line to `~/.toss-investor/decisions.jsonl`
(schema in `references/memory.md`).

## Intents -> actions

| User intent | Action |
|-------------|--------|
| "삼성전자 분석해줘" / "005930 봐줘" | full 8-stage run (종목명→코드는 `stocks`로 확인) |
| "이 종목 사도 될까?" | 8 stages + concrete entry plan |
| "지금 포트폴리오 점검해줘" | hand off to `toss-portfolio` |
| "백테스트해줘" | hand off to `toss-backtest` |
| "매수/매도해줘" | analyze, then after confirmation → `toss-trade` |
| "뭐 좀 골라봐" / "오늘 강한 종목" | `toss-screen` screening → short summary per candidate |
