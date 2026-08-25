---
name: toss-trade
description: >-
  한국 주식 주문 실행 스킬. "매수해줘", "삼성전자 팔아줘", "지정가 주문", "분할매수",
  "손절 주문 넣어줘" 요청 시 — 사용자 명시 확인 후에만 실제 주문을 실행한다.
  확인 전에는 절대 주문 API를 호출하지 않는다. Order execution — only after explicit
  user confirmation; never calls order APIs before the confirm gate.
---

# toss-trade — order execution (confirmation gate mandatory)

## Absolute rules

1. **Never call an order API until the user explicitly answers "확인"/"예"/
   "go".** Requests that are analysis-only ("사도 될까?") redirect to the
   toss-analyze skill.
2. Keys required: `TOSS_CLIENT_ID`/`TOSS_CLIENT_SECRET` (+ account header) —
   abort with guidance if absent.
3. Check the 6 risk gates (toss-analyze references/risk-gates.md) before
   ordering — refuse all buys when the kill switch is armed.
4. 주문은 KRX 정규장(09:00–15:30 KST)·장전·장후 시간에만 접수된다 —
   `toss.py market-calendar`로 확인, 폐장 시 다음 세션 안내.

## Pre-order checks

```bash
python3 scripts/toss.py tick 73500          # tick snap (floor)
python3 scripts/toss.py price-limits 005930 # 상한가/하한가 밴드 확인
python3 scripts/toss.py buying-power        # 현금 (매수 시)
python3 scripts/toss.py sellable 005930     # 매도 가능 수량 (매도 시)
python3 scripts/toss.py commissions         # 수수료율
```

Limit price: tick grid + 상하한가 밴드 안쪽. Quantity: integer shares,
round DOWN. 수수료 여유분 남기기.

## Order commands

| Purpose | Command |
|---------|---------|
| Limit buy | `python3 scripts/toss.py order buy 005930 --qty 10 --price 70000` |
| Market buy | `python3 scripts/toss.py order buy 005930 --qty 10` |
| Limit sell | `python3 scripts/toss.py order sell 005930 --qty 10 --price 72000` |
| Order detail | `python3 scripts/toss.py order-get <orderId>` |
| Open orders | `python3 scripts/toss.py orders --status OPEN` |
| Cancel | `python3 scripts/toss.py cancel <orderId>` |

Market orders carry slippage risk on thin books — prefer limit. 1억 KRW
이상 주문은 `confirm-high-value-required` 에러가 나면 사용자 재확인 후
재시도 안내 (스크립트가 플래그를 자동 올리지 않음 — 30억 이상은 API 거부).

## Confirmation format

Always confirm with the user in this shape before ordering:

```
주문 확인 요청
- 종목: 삼성전자 (005930)
- 구분: 지정가 매수
- 수량: 10주 @ 70,000 KRW (총 700,000 KRW)
- 손절 계획: 68,900 (진입 − 1.5×ATR14)
- 수수료: 약 105 KRW (0.015%)
실행할까요? (예/아니오)
```

## After ordering

1. Report the `orderId` immediately.
2. Track via `order-get` — FILLED/PARTIAL_FILLED/CANCELED 상태 보고.
3. Offer cancellation for unfilled limit orders.
4. Append the fill to `~/.toss-investor/decisions.jsonl` as one line
   (`"executed": true, "filled_price": ...`).

## Supported strategies (on request)

- **DCA**: split a buy into n limit orders at the stated interval — respect
  the per-minute order gate.
- **Stop-loss limit**: after a fill, place a limit sell at entry − 1.5×ATR
  (tick-snapped).
- **TP/SL**: Toss conditional-orders(OCO) API는 이 플러그인에서 미지원 —
  양쪽 지정가를 각각 넣고 한쪽 체결 시 수동 취소 안내.
