# Risk — 6 gates

Every order proposal must pass 6 gates. Soft gates attach warnings; hard gates
block the proposal outright.

| # | Gate | Type | Rule |
|---|------|------|------|
| 1 | price_band | soft | order price beyond preset ±% of current price → warn (flash-move protection) |
| 2 | max_single_position | soft | (held + new) / total assets (cash + valuation) ≤ preset % |
| 3 | max_total_invested | soft | total invested share ≤ preset % |
| 4 | warning block | soft | 활성 warning (OVERHEATED/INVESTMENT_WARNING/INVESTMENT_RISK/VI_*/LIQUIDATION_TRADING), `krxTradingSuspended`, 거래정지 → entry blocked with warning |
| 5 | max_orders_per_minute | soft | rate-limit proposals (anti rapid-retry) |
| 6 | daily_loss_limit | **hard** | day PnL / cash ≤ −limit ⇒ kill switch — all further proposals blocked |

Gate 4 data: `toss.py warnings {symbol}` + `toss.py stocks {symbol}`
(`koreanMarketDetail.krxTradingSuspended`). 상한가 근접(당일 등락 +25% 이상)도
과열로 취급 — KRX 상하한가는 ±30%.

## Presets

| Preset | max_single | max_total | price_band | daily_loss | warning block |
|--------|-----------|-----------|------------|-----------|----------------|
| conservative (default) | 15% | 50% | ±5% | −3% | on |
| momentum | 25% | 80% | ±10% | −8% | off |
| long_term | 20% | 60% | ±5% | −5% | on |

State the preset name in the report whenever the user overrides the default.

## Position sizing (calc_buy_quantity port)

```
quantity = floor(cash_buying_power × max_position_pct/100 ÷ entry_price)
```

KRX quantity is integer shares — always round DOWN (never round up —
prevents overspending cash). Sells: full holding or a specified quantity;
check `toss.py sellable {symbol}` first.

## Fees & taxes (KRX)

- Commission: read `toss.py commissions` (e.g. 0.015% KR). Keep a fee margin.
- Sell tax: ~0.15–0.2% (거래세, differs by 종목 유형) — assume ~0.2% on
 sells when estimating.
- 1억 KRW 이상 주문: API requires `confirmHighValueOrder` — the trade skill
 asks the user to re-confirm. 30억 이상: API rejects outright
 (`max-order-amount-exceeded`).

## KRX tick size (mandatory pre-order check)

| Price band (KRW) | Tick |
|---|---|
| < 2,000 | 1 |
| 2,000–5,000 | 5 |
| 5,000–20,000 | 10 |
| 20,000–50,000 | 50 |
| 50,000–200,000 | 100 |
| 200,000–500,000 | 500 |
| ≥ 500,000 | 1,000 |

Snap with `python3 scripts/toss.py tick <price>` (floors, never rounds up).
Limit prices must sit on the grid or the API rejects with the nearest valid
prices in `error.data.nearestPrices`. 상한가/하한가 from
`toss.py price-limits {symbol}` — limit prices outside the band are invalid.

## Kill switch (gate 6, hard)

On daily loss limit breach:
1. Block every further buy proposal (state the reason).
2. Propose full liquidation only with user confirmation.
3. Record the kill-switch event in `~/.toss-investor/decisions.jsonl`.

Daily loss = (day-start assets − current total assets) / day-start cash.
When uncomputable, approximate with holdings `dailyProfitLoss.amount` (KRW)
and mark it as approximate.
