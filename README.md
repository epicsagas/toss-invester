# toss-investor

**[한국어](README.md)** | [English](README_EN.md)

<p align="center">
 <a href="https://github.com/epicsagas/toss-invester/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/epicsagas/toss-invester?style=for-the-badge&labelColor=0d1117&color=ffd700&logo=github&logoColor=white" /></a>
 <a href="https://github.com/epicsagas/toss-invester/network/members"><img alt="Forks" src="https://img.shields.io/github/forks/epicsagas/toss-invester?style=for-the-badge&labelColor=0d1117&color=2ecc71&logo=github&logoColor=white" /></a>
 <a href="https://github.com/epicsagas/toss-invester/issues"><img alt="Issues" src="https://img.shields.io/github/issues/epicsagas/toss-invester?style=for-the-badge&labelColor=0d1117&color=ff6b6b&logo=github&logoColor=white" /></a>
 <a href="https://github.com/epicsagas/toss-invester/commits/main"><img alt="Last commit" src="https://img.shields.io/github/last-commit/epicsagas/toss-invester?style=for-the-badge&labelColor=0d1117&color=58a6ff&logo=git&logoColor=white" /></a>
 <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-3fb950?style=for-the-badge&labelColor=0d1117" /></a>
</p>

> 한국 주식(KRX 코스피·코스닥) 투자 멀티 에이전트 분석·매매 플러그인. TradingAgents 스타일 8단계 디비트 파이프라인을 AI 코딩 에이전트 플러그인 형태로 이식. 데이터·주문은 [토스증권 Open API](https://developers.tossinvest.com/docs).

"삼성전자 분석해줘" 한 문장으로 — 스냅샷 수집 → 시장 분석 → 불/곰 디비트 2라운드 → 리서치 매니저 5단계 판정(Buy/Overweight/Hold/Underweight/Sell) → 6대 리스크 게이트 → 포트폴리오 매니저 최종 판단 → 트레이더 주문 제안까지 8단계 파이프라인이 돈다. 실제 주문은 사용자 확인 전에 절대 실행되지 않는다.

## Features

| | 기능 | 왜 중요한가 |
|--|------|------------|
| 🥊 | 8단계 불/곰 디비트 파이프라인 | 단일 LLM 판정보다 편향·환각에 강한 구조화된 결정 |
| 🇰🇷 | KRX 규칙 내장 | 호가단위 스냅·상하한가(±30%)·정수 주수·투자유의/VI 차단 자동 처리 |
| 🌊 | 수급 데이터 분석 | 투자자별 순매수·공매도 비중이 불/곰 논거로 직접 인용됨 |
| 🔒 | 확인 게이트 + 6대 리스크 게이트 | 주문은 사용자 "예" 전까지 절대 전송 안 됨, 일일 손실 킬스위치 |
| 🧠 | 결정 저널·자기 성찰 | 과거 판단 회상으로 추격 매수·몰빵 패턴 스스로 경고 |
| 📦 | stdlib-only Python 스크립트 | 의존성 설치 0건, 에이전트 없이 CLI로도 단독 사용 |
| 🔌 | 4호스트 매니페스트 | Claude Code / Codex / Antigravity / Hermes 어디서든 동일 스킬 |

## 설치

**키 발급**: [토스증권 Open API](https://developers.tossinvest.com/)에서 클라이언트 자격증명(`client_id`/`client_secret`) 발급 후 `.env`에 설정. **시세 조회를 포함한 모든 API 호출에 키가 필요하다**.

```bash
cp .env.example .env   # TOSS_CLIENT_ID / TOSS_CLIENT_SECRET (+선택 TOSS_ACCOUNT_SEQ)
```

| 호스트 | 설치 |
|--------|------|
| Claude Code | `claude plugin marketplace add epicsagas/toss-invester` 후 `claude plugin install toss-investor@toss-investor`. skills 7종 + agents 7종 |
| Codex | `codex plugin marketplace add epicsagas/toss-invester` 후 `codex plugin add toss-investor@toss-investor` |
| Antigravity (agy) | `agy plugin install https://github.com/epicsagas/toss-invester` |
| Hermes | `hermes plugins install https://github.com/epicsagas/toss-invester --enable` |

스캐너 오탐 주의: 이 플러그인은 주문 API를 포함하나 **확인 게이트 없이는 절대 호출하지 않는다** — 정적 스캔이 "trading bot"으로 오탐할 수 있다.

## 바로 시작

```
삼성전자 분석해줘
005930 사도 될까?
거래대금 상위 종목 보여주고 상위 3개만 깊게 봐줘
내 포트폴리오 점검해줘
삼성전자 10주 지정가 70000에 매수해줘   ← 확인 요청 후 실행
```

## 어떻게 돌아가나

```
스냅샷 (캔들·시세·호가·상하한가·투자유의·수급·공매도·지수·과거 판단 회상)
 → 시장 분석가 (3-4문장 팩트 요약)
 → 강세론자 ⇄ 약세론자 × 2라운드     (모든 주장은 스냅샷 수치 인용)
 → 리서치 매니저 (5단계 판정 JSON, 디비트 승자 결정)
 → 리스크 매니저 (6대 게이트 + 포지션 사이징)
 → 포트폴리오 매니저 (과거 판단 회상 + 최종 오버라이드)
 → 트레이더 (주문 제안 JSON — 호가단위·상하한가 보정)
 → 결정 저널 append (~/.toss-investor/decisions.jsonl)
```

모든 단계에 종목 앵커("분석 대상: 삼성전자 (005930, 코스피)")가 박혀 있어 환각을 차단한다. 각 단계 실패는 안전 기본값(Hold)으로 강등 — 파이프라인은 중단되지 않는다.

## 왜 toss-investor인가

| | toss-investor | [TradingAgents] | 토스 앱 수동 |
|-|---------------|-----------------|--------------|
| 대상 시장 | KRX 코스피·코스닥 | 미국 주식 | 전부 |
| 실행 환경 | AI 코딩 에이전트 플러그인 | Python 연구 프레임워크 | 앱 |
| 실주문 게이트 | 확인제 + 6 게이트 | 연구 전용 (주문 없음) | 본인 조작 |
| 수급·호가 규칙 | 투자자별 순매수·공매도·tick/상하한가 | DART/뉴스 중심 | ✓ |
| 의존성 | 없음 (stdlib) | LangGraph 등 다수 | — |

[TradingAgents]: https://github.com/TauricResearch/TradingAgents

TradingAgents는 미국 주식 연구·백테스트 생태계가 더 깊고, 실시간 체결 화면은 토스 앱이 낫다. 이 플러그인은 "내 에이전트 안에서 한국 주식을 안전하게 분석·주문 제안까지"에 특화되어 있다.

## 안전장치

- **확인 게이트**: 주문 API는 사용자가 명시적으로 "예"를 답하기 전까지 호출 불가.
- **6대 리스크 게이트**: 가격 밴드 / 단일 종목 한도 / 총 투자 한도 / 투자유의·과열 차단 / 분당 주문 수 / 일일 손실 킬스위치(하드).
- **KRX 규칙 내장**: 호가단위 자동 스냅(버림), 상하한가(±30%) 밴드 검증, 정수 주수, 1억 이상 고액 주문 재확인, 수수료·매도세 반영.
- **결정 저널**: 모든 판단이 `~/.toss-investor/decisions.jsonl`에 기록되고 다음 분석 때 회상되어 몰빵 패턴·추격 매수를 자기 성찰한다.

## 스크립트 직접 사용 (에이전트 없이)

```bash
python3 scripts/toss.py prices 005930
python3 scripts/toss.py candles 005930 --interval 1d --count 200 | python3 scripts/indicators.py
python3 scripts/toss.py flow 005930                 # 투자자별 순매수
python3 scripts/screen.py --sort gainers --top 10
python3 scripts/toss.py candles 005930 --interval 1d --count 200 > /tmp/a.json
python3 scripts/backtest.py sma_cross --file /tmp/a.json
python3 scripts/test_indicators.py                  # 셀프체크
```

전 명령 목록: `python3 scripts/toss.py --help`. 표준 라이브러리만 사용하며, pip 설치 불필요. 성능·평가: [EVAL.md](EVAL.md) — 벤치마크 composite 1.0, 읽기 전용 엔드포인트 평균 149 ms.

## FAQ

- **Q. 키 없이 쓸 수 있나요?** 아니요 — Toss API는 시세 포함 전 엔드포인트가 OAuth2 클라이언트 자격증명을 요구합니다.
- **Q. 실시간 웹소켓은요?** Toss는 웹소켓(`wss://openapi-ws.tossinvest.com`)을 제공하지만 이 플러그인은 원샷 CLI 폴링 형태라 REST만 사용합니다.
- **Q. 조건부주문(OCO)은?** API로 제공되지만 이 플러그인 v0.1에서는 미지원 — 필요시 `scripts/toss.py` 확장.
- **Q. 미국 주식도 되나요?** API는 US 시장도 지원하지만 파이프라인 프롬프트는 KRX 기준입니다.

## 기여

이슈·PR 환영. 버그 수정은 `python3 scripts/test_indicators.py` 통과를, 문서 변경은 한국어·영어(README_EN.md) 동시 갱신을 지켜주세요.

## 감사의 글 (Acknowledgements)

- [TradingAgents](https://github.com/TauricResearch/TradingAgents) — 다중 에이전트 디비트 파이프라인 원형.
- [tossinvest-sdk](https://github.com/epicsagas/tossinvest-sdk) — 와이어 규격 참조용 비공식 Rust SDK.

## 라이선스

MIT — [LICENSE](LICENSE)

## 면책 조항 (Disclaimer)

본 프로젝트는 토스증권 Open API의 **비공식** 연구용 플러그인이며 토스증권과 무관합니다. '토스증권' 및 'Toss' 상표권은 비바리퍼블리카/토스증권에 있습니다. 모든 분석은 투자 참고용이며 투자 판단과 그에 따른 손익의 책임은 사용자에게 있습니다. 실제 주문 실행 전 반드시 내용을 확인하십시오.
