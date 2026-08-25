---
name: toss-screen
description: >-
  한국 주식 스크리닝 스킬. "거래대금 많은 종목", "오늘 급등 종목", "급락 종목",
  "투자 후보 골라줘", "외국인 많이 사는 종목" 요청 시 Toss 랭킹 기반 조건 필터 후
  후보 리스트를 뽑고 필요시 상위 후보 지표·수급 분석까지 이어간다. KRX market
  screening by trading amount/gainers/losers with follow-up indicator analysis.
---

# toss-screen — market screening

Needs Toss keys. Rankings cover 상위 100위까지.

## Commands

```bash
python3 scripts/screen.py --top 10 --sort volume          # 거래대금 상위
python3 scripts/screen.py --top 10 --sort gainers         # 급상승 (등락률 상위)
python3 scripts/screen.py --top 10 --sort losers          # 급하락
python3 scripts/screen.py --top 20 --min-amount 1e10      # 유동성 필터 (100억)
python3 scripts/screen.py --top 10 --duration 1w          # 기간: realtime~1y
python3 scripts/screen.py --top 10 --exclude-caution     # 투자유의 종목 제외
```

Output fields: rank/symbol/name/price/change_pct/trading_volume/
trading_amount_krw. `TOP_GAINERS`/`TOP_LOSERS`는 `realtime` 미지원 —
`--duration 1d` 이상 사용.

## Deep dive on candidates (on request)

For the top candidates (default 5):

```bash
python3 scripts/toss.py candles <symbol> --interval 1d --count 200 | python3 scripts/indicators.py
python3 scripts/toss.py flow <symbol>          # 투자자별 순매수
python3 scripts/toss.py warnings <symbol>      # 과열/투자유의 여부
```

## Interpretation rules

- 당일 등락 +25% 이상은 상한가(+30%) 근접 — 과열 게이트 대상이므로 진입
  권고 없이 관찰만.
- 투자유의(INVESTMENT_WARNING/RISK)·정리매매 종목은 `--exclude-caution`으로
  걸러지지 않은 경우 반드시 보고에 명시.
- Screening discovers; the final call belongs to the toss-analyze 8-stage
  pipeline.
- Cross-correlation (optional): `backtest.py correlate a.json b.json`
  between candidates — pearson > 0.8 pairs are effectively one exposure
  (특히 동일 업종/테마) — warn.

## Output format

Table: rank/symbol/name/price/day change/trading amount/one-line comment.
Deep-dive results in a separate section.
