# AGENTS.md — toss-investor

Role: ports the multi-agent deep-analysis FSM (TradingAgents-style 8-stage
debate) to Korean equities (KRX 코스피/코스닥) via the Toss Securities Open API.

## Absolute rules

1. **NEVER call order/cancel endpoints without explicit user confirmation.**
   Order execution lives only in the toss-trade skill, behind a confirm gate.
   출금/이체 API는 존재하지도 않는다 — 절대 시도하지 마라.
2. **Every Toss call needs OAuth2 client credentials** —
   `TOSS_CLIENT_ID`/`TOSS_CLIENT_SECRET`. Unlike Upbit there are NO keyless
   public endpoints: 시세 조회조차 키가 필요하다. Account/asset/order calls
   additionally resolve an account (env `TOSS_ACCOUNT_SEQ` or auto-pick the
   first BROKERAGE account). No keys ⇒ explain and stop.
3. Scripts are stdlib-only Python under `scripts/`; run as
   `python3 scripts/...` from the plugin root.
4. All numeric API fields arrive as strings — never float-compare raw
   payloads blindly.

## Intent → skill dispatch

| Intent | Skill |
|--------|-------|
| "삼성전자 분석해줘" / "005930 사도 될까" | toss-analyze (8-stage) |
| "지금 시세", "호가", "순매수", "코스피 지수" | toss-market-data |
| "RSI", "MACD", "추세", "지표 분석" | toss-technical |
| "거래대금 많은 종목", "급등/급락" | toss-screen |
| "포트폴리오 점검", "수익률 어때" | toss-portfolio |
| "백테스트해줘", "상관관계" | toss-backtest |
| "매수/매도해줘" (실행 의도) | toss-trade (confirm gate) |

## Sub-agents (pipeline roles)

market-analyst → bull-researcher / bear-researcher (2 rounds) →
research-manager (5-tier verdict) → risk-manager (6 gates) →
portfolio-manager (final override) → trader (order proposal only).

Journal: `~/.toss-investor/decisions.jsonl` (schema in toss-analyze
references/memory.md). Token cache: `~/.toss-investor/token.json`.

## Host differences

- **Claude Code**: skills/ + agents/ (7 sub-agents).
- **Codex**: skills/ + `.codex-plugin/agents/*.toml` (keep in sync with the
  .md files).
- **agy / Hermes**: skills only — the 7 roles run inline, sequentially, in
  the main session.
