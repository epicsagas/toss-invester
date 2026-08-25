#!/usr/bin/env python3
"""Screen KRX markets via Toss rankings — stdlib only.

Sort key maps to a rankings `--type`: volume→거래대금 상위, gainers→급상승,
losers→급하락. Names resolved in bulk from /api/v1/stocks (≤200).

Usage: screen.py [--top 10] [--sort volume|gainers|losers] [--duration 1d]
                 [--min-amount 0] [--exclude-caution]
Requires TOSS_CLIENT_ID / TOSS_CLIENT_SECRET.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from toss import api  # noqa: E402

SORT_TO_TYPE = {
    "volume": "MARKET_TRADING_AMOUNT",
    "gainers": "TOP_GAINERS",
    "losers": "TOP_LOSERS",
}


def main():
    p = argparse.ArgumentParser(description="Toss KRX market screener")
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--sort", choices=list(SORT_TO_TYPE), default="volume")
    p.add_argument("--duration", default="1d",
                   choices=["realtime", "1d", "1w", "1mo", "3mo", "6mo", "1y"])
    p.add_argument("--min-amount", type=float, default=0,
                   help="min trading amount in KRW for the chosen duration")
    p.add_argument("--exclude-caution", action="store_true")
    args = p.parse_args()

    params = {"type": SORT_TO_TYPE[args.sort], "marketCountry": "KR",
              "duration": args.duration, "count": min(max(args.top, 1), 100)}
    if args.exclude_caution:
        params["excludeInvestmentCaution"] = "true"
    res = api("GET", "/api/v1/rankings", params)

    rows = [r for r in res.get("rankings", [])
            if float(r.get("tradingAmount") or 0) >= args.min_amount]
    symbols = ",".join(r["symbol"] for r in rows)
    names = {s["symbol"]: s.get("name") for s in
             (api("GET", "/api/v1/stocks", {"symbols": symbols}) if symbols else [])}

    out = [{"rank": r["rank"], "symbol": r["symbol"], "name": names.get(r["symbol"]),
            "price": r["price"]["lastPrice"],
            "change_pct": round(float(r["price"].get("changeRate") or 0) * 100, 2),
            "trading_volume": r["tradingVolume"],
            "trading_amount_krw": int(float(r["tradingAmount"]))}
           for r in rows[:args.top]]
    print(json.dumps({"ranked_at": res.get("rankedAt"), "rows": out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
