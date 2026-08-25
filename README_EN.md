# toss-investor

[한국어](README.md) | **[English](README_EN.md)**

<p align="center">
 <a href="https://github.com/epicsagas/toss-invester/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/epicsagas/toss-invester?style=for-the-badge&labelColor=0d1117&color=ffd700&logo=github&logoColor=white" /></a>
 <a href="https://github.com/epicsagas/toss-invester/network/members"><img alt="Forks" src="https://img.shields.io/github/forks/epicsagas/toss-invester?style=for-the-badge&labelColor=0d1117&color=2ecc71&logo=github&logoColor=white" /></a>
 <a href="https://github.com/epicsagas/toss-invester/issues"><img alt="Issues" src="https://img.shields.io/github/issues/epicsagas/toss-invester?style=for-the-badge&labelColor=0d1117&color=ff6b6b&logo=github&logoColor=white" /></a>
 <a href="https://github.com/epicsagas/toss-invester/commits/main"><img alt="Last commit" src="https://img.shields.io/github/last-commit/epicsagas/toss-invester?style=for-the-badge&labelColor=0d1117&color=58a6ff&logo=git&logoColor=white" /></a>
 <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-3fb950?style=for-the-badge&labelColor=0d1117" /></a>
</p>

> Multi-agent KRX stock analysis & trading plugin for AI coding agents — one sentence in, 8-stage debate report out. Powered by the [Toss Securities Open API](https://developers.tossinvest.com/docs).

> This is a translation of [README.md](README.md). The Korean version is the authoritative source and may be more up-to-date.

Say "Analyze Samsung Electronics" and an 8-stage pipeline runs: snapshot collection → market analysis → bull/bear debate ×2 rounds → research manager 5-tier verdict (Buy/Overweight/Hold/Underweight/Sell) → 6 risk gates → portfolio manager final call → trader order proposal. **Real orders are never placed without explicit user confirmation.**

## Features

| | Feature | Why it matters |
|--|---------|----------------|
| 🥊 | 8-stage bull/bear debate pipeline | Structured decisions resist single-LLM bias and hallucination |
| 🇰🇷 | KRX rules built in | Tick-size snapping, ±30% price limits, integer shares, warning/VI blocks — automatic |
| 🌊 | Supply/demand analysis | Investor net-buy volumes and short-selling ratios cited directly as debate evidence |
| 🔒 | Confirm gate + 6 risk gates | Orders never send before the user says "yes"; daily-loss kill switch |
| 🧠 | Decision journal & self-reflection | Past decisions recalled to flag momentum-chasing and concentration |
| 📦 | stdlib-only Python scripts | Zero dependencies; usable standalone from the CLI without any agent |
| 🔌 | 4 host manifests | Same skills on Claude Code / Codex / Antigravity / Hermes |

## Installation

**Get keys**: issue OAuth2 client credentials (`client_id`/`client_secret`) at the [Toss Securities Open API portal](https://developers.tossinvest.com/) and put them in `.env`. **Every API call — including market data — requires keys** (there are no keyless public endpoints).

```bash
cp .env.example .env   # TOSS_CLIENT_ID / TOSS_CLIENT_SECRET (+optional TOSS_ACCOUNT_SEQ)
```

The `.env` next to the plugin root is auto-loaded; existing environment variables take precedence.

| Host | Install |
|------|---------|
| Claude Code | add this directory to your plugin paths (`/plugin` → local marketplace or direct path). 7 skills + 7 agents |
| Codex | `.codex-plugin/` manifest + `skills/` |
| Antigravity (agy) | root `plugin.json` |
| Hermes | `~/.hermes/plugins/toss-investor/` (`plugin.yaml` + `__init__.py`) |

Scanner false-positive note: this plugin includes order endpoints but **never calls them without the confirmation gate** — static scanners may flag it as a "trading bot".

## Getting started

```
Analyze Samsung Electronics                     (full 8-stage run)
Is 005930 a buy?
Show top stocks by trading amount, deep-dive the top 3
Review my portfolio
Buy 10 shares of Samsung Electronics at 70000   ← asks for confirmation first
```

## How it works

```
Snapshot (candles · prices · orderbook · price limits · warnings ·
          supply/demand · short selling · indices · past-decision recall)
 → Market analyst (3-4 sentence fact summary)
 → Bull ⇄ Bear × 2 rounds          (every claim cites a snapshot number)
 → Research manager (5-tier JSON verdict, debate winner)
 → Risk manager (6 gates + position sizing)
 → Portfolio manager (past-decision recall + final override)
 → Trader (order proposal JSON — tick/price-limit adjusted)
 → Append to decision journal (~/.toss-investor/decisions.jsonl)
```

Every stage carries the instrument anchor ("Analysis target: Samsung Electronics (005930, KOSPI)") to block hallucination. A failed stage degrades to a safe default (Hold) — the pipeline never aborts.

## Why toss-investor?

| | toss-investor | [TradingAgents] | Toss app, manual |
|-|---------------|-----------------|------------------|
| Market | KRX (KOSPI/KOSDAQ) | US equities | all |
| Runs as | AI coding agent plugin | Python research framework | mobile app |
| Order gate | confirm + 6 gates | research only (no orders) | you |
| Supply/demand & tick rules | net-buy · short-selling · tick/limits | DART/news centric | ✓ |
| Dependencies | none (stdlib) | LangGraph & more | — |

[TradingAgents]: https://github.com/TauricResearch/TradingAgents

TradingAgents has the deeper US-equity research ecosystem, and the Toss app is better at live execution screens. This plugin specializes in "safe analysis through order proposal for Korean equities, inside my agent".

## Safety

- **Confirm gate**: order APIs are unreachable until the user explicitly says yes.
- **6 risk gates**: price band / single-position cap / total-invested cap / warning & overheat block / orders-per-minute / daily-loss kill switch (hard).
- **KRX rules built in**: tick snapping (floor), ±30% price-limit band validation, integer shares, ≥100M KRW high-value reconfirmation, commission + sell tax accounted.
- **Decision journal**: every verdict is recorded in `~/.toss-investor/decisions.jsonl` and recalled in later analyses, so the pipeline self-flags concentration and momentum-chasing patterns.

## Using the scripts directly (no agent)

```bash
python3 scripts/toss.py prices 005930
python3 scripts/toss.py candles 005930 --interval 1d --count 200 | python3 scripts/indicators.py
python3 scripts/toss.py flow 005930                 # investor net-buy volumes
python3 scripts/screen.py --sort gainers --top 10
python3 scripts/toss.py candles 005930 --interval 1d --count 200 > /tmp/a.json
python3 scripts/backtest.py sma_cross --file /tmp/a.json
python3 scripts/test_indicators.py                  # self-checks
```

Full command list: `python3 scripts/toss.py --help`. Standard library only — no pip installs. Benchmarks: [EVAL.md](EVAL.md) — composite 1.0, 149 ms average per read-only endpoint.

## FAQ

- **Can I use it without keys?** No — the Toss API requires OAuth2 client credentials on every endpoint, including market data.
- **What about the realtime WebSocket?** Toss offers one (`wss://openapi-ws.tossinvest.com`), but this plugin is a one-shot CLI polling design, so it uses REST only.
- **Conditional (OCO) orders?** Available in the API but not supported in v0.1 — extend `scripts/toss.py` if you need them.
- **US stocks?** The API supports US markets, but the pipeline prompts are tuned for KRX.

## Contributing

Issues and PRs welcome. Bug fixes must pass `python3 scripts/test_indicators.py`; doc changes should update the Korean and English READMEs together.

## Acknowledgements

- [TradingAgents](https://github.com/TauricResearch/TradingAgents) — the multi-agent debate pipeline this work follows.
- [tossinvest-sdk](https://github.com/epicsagas/tossinvest-sdk) — unofficial Rust SDK used as the wire-spec reference.

## License

MIT — [LICENSE](LICENSE)

## Disclaimer

This is an **unofficial** research plugin for the Toss Securities Open API and is not affiliated with Toss Securities. The "토스증권"/"Toss" trademarks belong to Viva Republica / Toss Securities. All analysis is for reference only; the user bears full responsibility for investment decisions and outcomes. Always review order details before any execution.
