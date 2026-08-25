# 8-stage pipeline detail

Source: TradingAgents-style deep-analysis FSM adapted to
KRX via the Toss Open API. Hierarchical judges — no voting. Each stage's
output is inherited as input by the next.

## Common anchor (prepend to every role prompt)

```
분석 대상: {종목명} (종목코드 {005930}, {코스피|코스닥}). 이 종목만 분석하며,
모든 수치는 아래 제공된 실시간 데이터(캔들/시세/호가/지표/수급 JSON)를
단일 진실 원천으로 사용한다. 데이터에 없는 수치를 만들어 내지 마라.
```

Core anti-hallucination device (instrument anchoring). Attach the snapshot
data to the prompt.

## Snapshot composition (stage 1, gather)

- prices: 현재가 (`toss.py prices`)
- daily 200 + 1m 200 candles (`toss.py candles`) — Toss has 1m/1d only,
 no 60m; the 1m tail covers intraday timing
- indicator batch JSON (`indicators.py`): SMA20/60, EMA12/26, RSI14,
 MACD(12,26,9), Bollinger(20,2), ATR14, Stochastic, VWAP, OBV,
 returns (1/7/30d), trend
- orderbook: best bid/ask, totals (supply balance)
- trades: last 50 ticks
- price-limits: 당일 상한가/하한가 (KRX ±30% band)
- warnings: 투자유의/투자경고/정기과열/VI/정리매매 활성 여부
- stocks: 시장(KOSPI/KOSDAQ), 거래정지 여부(krxTradingSuspended)
- 수급: `toss.py flow {symbol}` (개인/외국인/기관/기타법인 순매수,
 외국인 보유율) + `toss.py short-selling {symbol}` (공매도 비중)
- 시장 컨텍스트: `index prices KOSPI,KOSDAQ` + `market-flow KOSPI` (시장
 수급) + `market-calendar` (장 상태)
- (keys) holdings/buying-power: 보유 수량·평균단가·손익, 현금
- (keys) journal recall 3: last 3 decisions for this symbol from
 `~/.toss-investor/decisions.jsonl` —
 "- [YYYY-MM-DD] {rating} — confidence {n}% — thesis gist"
- (web tools) recent news/공시 headlines 3-5 — Korean equities are
 news/공시-sensitive

## Free-text stages (quick tier, concise Korean output)

Common tone: "당신은 한국 주식 투자 분석 전문가다. 간결하고 근거 있는
한국어로 답하라."

| Role | Prompt gist |
|------|-------------|
| Market analyst | "기술/시장 분석을 3-4문장: 추세, 변동성, 거래량 이상, 지표 읽기 + 수급 한 줄." |
| Bull round 1 | "당신은 강세론자다. 매수 근거를 2-3문장으로 강하게 주장." |
| Bear round 1 | "당신은 약세론자다. 매도/관망 근거를 독립적으로 2-3문장." |
| Bull round 2 | "약세론자 주장을 직접 반박." |
| Bear round 2 | "강세론자 주장을 직접 반박." |

Rules: every claim cites a snapshot number. No unsupported narratives.
A failed stage degrades to an empty placeholder — never abort the run
(resilient). The market analyst is pipeline-critical — on failure, re-collect
the snapshot once and retry; abort only if that fails.

## Structured stages (deep tier, JSON enforced)

### Research manager (debate judge)

```json
{"rating": "Buy|Overweight|Hold|Underweight|Sell",
 "confidence": 0.0,
 "debate_winner": "bull|bear|tie",
 "key_thesis": "one sentence",
 "catalysts": ["catalyst 1", "..."],
 "risks": ["risk 1", "..."],
 "price_target": null,
 "time_horizon": "short|mid|long"}
```

Embed the example JSON verbatim in the prompt: "다른 필드명·배열/문자열
타입 불일치·설명문·<think> 블록 금지. JSON 객체 1개만 출력."

### Risk manager (overlay)

```json
{"overall_risk": "Low|Medium|High",
 "gates": [{"gate": "...", "status": "pass|warn|blocked", "detail": "..."}],
 "kill_switch": false,
 "max_position_pct": 0,
 "position_size": {"quantity": 0, "estimated_amount_krw": 0},
 "risk_factors": ["..."],
 "mitigation": ["..."]}
```

Reflects the 6-gate outcome (risk-gates.md) into max_position_pct.

### Portfolio manager (final override)

```json
{"rating": "Buy|Overweight|Hold|Underweight|Sell",
 "executive_summary": "one paragraph",
 "investment_thesis": "single sentence, not an array",
 "price_target": null,
 "time_horizon": "short|mid|long",
 "override_reason": null}
```

Past-decision recall injected. If risk max_position_pct exceeds the preset
single-position cap, append "⚠ 권장 최대 포지션 초과 — 비중 축소 권고" to
the summary. null override_reason when agreeing with the research manager.

### Trader (order proposal)

```json
{"action": "Buy|Hold|Sell",
 "order_type": "market|limit",
 "symbol": "005930",
 "entry_price": 0,
 "quantity": 0,
 "estimated_amount_krw": 0,
 "stop_loss": 0,
 "take_profit": 0,
 "split_entries": 1,
 "rationale": "one sentence"}
```

"Hold: emit only {\"action\": \"Hold\", \"rationale\": \"...\"}." Stop-loss
default: entry − 1.5×ATR14. Entry price must sit on the KRX tick grid
(`toss.py tick`) and inside the day's 상한가/하한가.

## JSON parsing defenses (GLM/local-model hardening — full original kit)

1. Attempt 1: JSON schema enforced, temp 0.3. On failure:
2. Attempt 2: plain JSON mode, temp 0.1, suffix "반드시 JSON 객체 1개만
 출력한다. 마크다운 코드펜스, 설명문, 한국어 장문 텍스트는 금지",
 max_tokens doubled.
3. Pre-parse: strip `<think>` blocks, remove code fences, unwrap single-key
 objects (`{"result": {...}}` → inner), absorb field aliases
 (investment_rating/manager_decision/thesis → rating etc.), coerce "25%"
 → 25.0, join arrays where a string is expected.
4. Final failure → safe defaults (Hold / confidence 0 / risk Medium) with an
 explicit "parse failure, defaults used" note. Never abort the run.

## rating normalization (normalize_rating)

Absorb Korean/abbreviations: "매수"/"강력매수"/"strong buy"→Buy,
"OW"/"over"→Overweight, "보류"/"관망"/"중립"/"neutral"→Hold,
"UW"/"under"→Underweight, "매도"/"강력매도"→Sell. **Unknown → Hold (safe
fallback).**

## Decision journal append schema (after stage 8)

```json
{"symbol": "005930", "name": "삼성전자", "date": "2026-08-26",
 "rating": "Buy", "confidence": 0.72, "price_target": 80000,
 "time_horizon": "mid", "risk_grade": "Medium", "max_position_pct": 15,
 "order_proposed": false, "price_at_decision": 72000,
 "key_thesis": "...", "supersedes": "<date of previous decision for this symbol>"}
```

`supersedes` links only to the immediately previous decision FOR THE SAME
symbol (temporal spine — linking against the whole recall set causes
cross-symbol mislinks; this exact failure mode was measured at 14/25 bad
links). Track direction changes: code ratings as ±1/0, compare with the
previous decision — agrees_with / maintains / reverses / initiates.
