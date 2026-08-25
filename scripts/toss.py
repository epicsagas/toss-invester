#!/usr/bin/env python3
"""Toss Securities Open API (v1.2.14) wrapper — stdlib only.

Every call (market data included) needs OAuth2 client credentials:
TOSS_CLIENT_ID / TOSS_CLIENT_SECRET. Account/asset/order calls also need an
account, from TOSS_ACCOUNT_SEQ or auto-picked (first BROKERAGE account).
TOSS_BASE_URL overrides the server (mock/staging).

Usage:
  toss.py prices 005930 [000660,...]
  toss.py candles 005930 --interval 1d|1m [--count 200] [--before TS] [--no-adjusted] [--with-next]
  toss.py orderbook 005930
  toss.py trades 005930 [--count 50]
  toss.py price-limits 005930
  toss.py stocks 005930 [000660,...]        # names/market/status lookup (≤200)
  toss.py warnings 005930                    # 투자유의/VI/정리매매
  toss.py rankings --type MARKET_TRADING_AMOUNT|MARKET_TRADING_VOLUME|TOP_GAINERS|TOP_LOSERS|TOSS_SECURITIES_TRADING_AMOUNT|TOSS_SECURITIES_TRADING_VOLUME \
      [--country KR] [--duration 1d] [--count 30] [--exclude-caution]
  toss.py exchange-rate --base KRW --quote USD
  toss.py market-calendar [--date 2026-08-26]
  toss.py index prices KOSPI,KOSDAQ
  toss.py index candles KOSPI --interval 1d --count 200
  toss.py market-flow KOSPI --interval 1d|1w|1mo|1y [--count 10]   # 시장 투자자별 매매대금
  toss.py flow 005930 [--count 10] [--until 2026-08-26]            # 종목별 투자자 매매동향
  toss.py short-selling 005930 [--count 10] [--until 2026-08-26]
  toss.py accounts
  toss.py holdings [--symbol 005930]
  toss.py buying-power [--currency KRW]
  toss.py sellable 005930
  toss.py commissions
  toss.py orders [--status OPEN|CLOSED] [--symbol 005930]
  toss.py order-get <orderId>
  toss.py order buy|sell 005930 --qty 10 [--price 70000]   # LIMIT needs --price, MARKET forbids it
  toss.py cancel <orderId>
  toss.py tick 73500                                          # KRX tick-size snap helper

Output: JSON on stdout. Candles are normalized oldest-first to upbit-style
keys (market/candle_date_time_utc/opening_price/high_price/low_price/
trade_price/volume) so indicators.py/backtest.py consume them unchanged.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def _load_dotenv():
    """Load ./.env next to the plugin root. Real environment wins."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))
    except OSError:
        pass


_load_dotenv()

BASE = os.environ.get("TOSS_BASE_URL", "https://openapi.tossinvest.com")
TOKEN_CACHE = os.path.expanduser("~/.toss-investor/token.json")
RETRY_STATUS = {429, 500, 502, 503}

# KRX 호가단위 (원)
TICK_TABLE = [
    (2000, 1), (5000, 5), (20000, 10), (50000, 50),
    (200000, 100), (500000, 500), (float("inf"), 1000),
]


def die(msg, code=1):
    print(json.dumps({"error": msg}, ensure_ascii=False), file=sys.stderr)
    sys.exit(code)


def out(obj):
    print(json.dumps(obj, ensure_ascii=False))


def tick_size(price: float) -> int:
    for upper, tick in TICK_TABLE:
        if price < upper:
            return tick
    return 1000


def snap_to_tick(price: float) -> int:
    tick = tick_size(price)
    return int(price // tick) * tick


def _load_cached_token() -> str | None:
    try:
        with open(TOKEN_CACHE) as f:
            cache = json.load(f)
        if cache.get("base_url") != BASE:
            return None
        if cache.get("expires_at", 0) > time.time() + 60:  # 60s early refresh
            return cache["access_token"]
    except (OSError, ValueError, KeyError):
        pass
    return None


def _token() -> str:
    cached = _load_cached_token()
    if cached:
        return cached
    cid = os.environ.get("TOSS_CLIENT_ID", "")
    secret = os.environ.get("TOSS_CLIENT_SECRET", "")
    if not cid or not secret:
        die("TOSS_CLIENT_ID / TOSS_CLIENT_SECRET not set", 2)
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": cid,
        "client_secret": secret,
    }).encode()
    req = urllib.request.Request(
        BASE + "/oauth2/token", data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            tok = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        die(f"token issue failed: HTTP {e.code} {e.read().decode('utf-8', 'replace')[:200]}", 2)
    except urllib.error.URLError as e:
        die(f"token issue failed: {e.reason}", 2)
    cache = {
        "base_url": BASE,
        "access_token": tok["access_token"],
        "expires_at": time.time() + int(tok.get("expires_in", 86400)),
    }
    try:
        os.makedirs(os.path.dirname(TOKEN_CACHE), exist_ok=True)
        with open(TOKEN_CACHE, "w") as f:
            json.dump(cache, f)
    except OSError:
        pass  # cache write best-effort
    return cache["access_token"]


def _account_seq() -> str:
    seq = os.environ.get("TOSS_ACCOUNT_SEQ", "")
    if seq:
        return seq
    for acc in api("GET", "/api/v1/accounts"):
        if acc.get("accountType") == "BROKERAGE":
            return str(acc["accountSeq"])
    die("no BROKERAGE account found; set TOSS_ACCOUNT_SEQ", 2)


def api(method: str, path: str, params: dict | None = None,
        body: dict | None = None, account: bool = False,
        _retried: bool = False):
    """Call the API; return the unwrapped `result`. Retries once on 429/5xx."""
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"Authorization": "Bearer " + _token()}
    if account:
        headers["X-Tossinvest-Account"] = _account_seq()
    data = json.dumps(body).encode() if body is not None else None
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        if e.code in RETRY_STATUS and not _retried:
            wait = e.headers.get("Retry-After") or e.headers.get("X-RateLimit-Reset") or 1
            try:
                time.sleep(min(float(wait), 5.0))
            except ValueError:
                time.sleep(1.0)
            return api(method, path, params, body, account, _retried=True)
        try:
            err = json.loads(raw).get("error", {})
            msg = f"{err.get('code', e.code)}: {err.get('message', '')}"
            if err.get("data"):
                msg += f" data={json.dumps(err['data'], ensure_ascii=False)}"
            die(f"{msg} (requestId {err.get('requestId', '?')})")
        except ValueError:
            die(f"HTTP {e.code}: {raw[:200]}")
    except urllib.error.URLError as e:
        die(f"request failed: {e.reason}", 2)
    if "result" not in payload:
        die(f"unexpected response (no result envelope): {str(payload)[:200]}")
    return payload["result"]


def normalize_candle(symbol: str, c: dict) -> dict:
    """Toss candle → upbit-shaped candle (floats). Caller reverses to oldest-first."""
    return {
        "market": symbol,
        "candle_date_time_utc": c.get("timestamp"),
        "opening_price": float(c["openPrice"]),
        "high_price": float(c["highPrice"]),
        "low_price": float(c["lowPrice"]),
        "trade_price": float(c["closePrice"]),
        "volume": float(c.get("volume") or 0),
    }


def main():
    p = argparse.ArgumentParser(
        description="Toss Securities Open API wrapper (stdlib only)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name):
        return sub.add_parser(name)

    add("prices").add_argument("symbols")  # comma-joined
    c = add("candles")
    c.add_argument("symbol")
    c.add_argument("--interval", default="1d", choices=["1m", "1d"])
    c.add_argument("--count", type=int, default=200)
    c.add_argument("--before")
    c.add_argument("--no-adjusted", action="store_true")
    c.add_argument("--with-next", action="store_true",
                   help="emit {candles, nextBefore} instead of a bare array")
    add("orderbook").add_argument("symbol")
    t = add("trades")
    t.add_argument("symbol")
    t.add_argument("--count", type=int, default=50)
    add("price-limits").add_argument("symbol")
    add("stocks").add_argument("symbols")
    add("warnings").add_argument("symbol")
    r = add("rankings")
    r.add_argument("--type", required=True,
                   choices=["MARKET_TRADING_AMOUNT", "MARKET_TRADING_VOLUME", "TOP_GAINERS",
                            "TOP_LOSERS", "TOSS_SECURITIES_TRADING_AMOUNT",
                            "TOSS_SECURITIES_TRADING_VOLUME"])
    r.add_argument("--country", default="KR", choices=["KR", "US"])
    r.add_argument("--duration", default="1d",
                   choices=["realtime", "1d", "1w", "1mo", "3mo", "6mo", "1y"])
    r.add_argument("--count", type=int, default=30)
    r.add_argument("--exclude-caution", action="store_true")
    e = add("exchange-rate")
    e.add_argument("--base", default="KRW")
    e.add_argument("--quote", default="USD")
    mc = add("market-calendar")
    mc.add_argument("--date")
    ip = add("index-prices"); ip.add_argument("symbols")  # KOSPI,KOSDAQ,KR_BOND_*
    ic = add("index-candles")
    ic.add_argument("symbol")
    ic.add_argument("--interval", default="1d", choices=["1m", "1d"])
    ic.add_argument("--count", type=int, default=200)
    ic.add_argument("--before")
    ic.add_argument("--with-next", action="store_true")
    mf = add("market-flow")  # 시장 투자자별 매매대금 (KOSPI/KOSDAQ)
    mf.add_argument("symbol", choices=["KOSPI", "KOSDAQ"])
    mf.add_argument("--interval", default="1d", choices=["1d", "1w", "1mo", "1y"])
    mf.add_argument("--count", type=int, default=10)
    mf.add_argument("--until")
    fl = add("flow")  # 종목별 투자자 매매동향 (KR only)
    fl.add_argument("symbol")
    fl.add_argument("--count", type=int, default=10)
    fl.add_argument("--until")
    ss = add("short-selling")
    ss.add_argument("symbol")
    ss.add_argument("--count", type=int, default=10)
    ss.add_argument("--until")
    add("accounts")
    h = add("holdings"); h.add_argument("--symbol")
    bp = add("buying-power"); bp.add_argument("--currency", default="KRW", choices=["KRW", "USD"])
    add("sellable").add_argument("symbol")
    add("commissions")
    o = add("orders")
    o.add_argument("--status", default="OPEN", choices=["OPEN", "CLOSED"])
    o.add_argument("--symbol")
    add("order-get").add_argument("order_id")
    od = add("order")
    od.add_argument("side", choices=["buy", "sell"])
    od.add_argument("symbol")
    od.add_argument("--qty", required=True)
    od.add_argument("--price", help="KRW limit price; omit for MARKET order")
    add("cancel").add_argument("order_id")
    add("tick").add_argument("price", type=float)

    a = p.parse_args()

    if a.cmd == "tick":
        out({"price": a.price, "tick": tick_size(a.price), "snapped": snap_to_tick(a.price)})
    elif a.cmd == "prices":
        out(api("GET", "/api/v1/prices", {"symbols": a.symbols}))
    elif a.cmd == "candles":
        params = {"symbol": a.symbol, "interval": a.interval, "count": a.count,
                  "adjusted": not a.no_adjusted}
        if a.before:
            params["before"] = a.before
        res = api("GET", "/api/v1/candles", params)
        candles = [normalize_candle(a.symbol, c) for c in reversed(res["candles"])]
        out({"candles": candles, "nextBefore": res.get("nextBefore")} if a.with_next else candles)
    elif a.cmd == "index-candles":
        params = {"interval": a.interval, "count": a.count}
        if a.before:
            params["before"] = a.before
        res = api("GET", f"/api/v1/market-indicators/{a.symbol}/candles", params)
        candles = [normalize_candle(a.symbol, c) for c in reversed(res["candles"])]
        out({"candles": candles, "nextBefore": res.get("nextBefore")} if a.with_next else candles)
    elif a.cmd == "orderbook":
        out(api("GET", "/api/v1/orderbook", {"symbol": a.symbol}))
    elif a.cmd == "trades":
        out(api("GET", "/api/v1/trades", {"symbol": a.symbol, "count": a.count}))
    elif a.cmd == "price-limits":
        out(api("GET", "/api/v1/price-limits", {"symbol": a.symbol}))
    elif a.cmd == "stocks":
        out(api("GET", "/api/v1/stocks", {"symbols": a.symbols}))
    elif a.cmd == "warnings":
        out(api("GET", f"/api/v1/stocks/{a.symbol}/warnings"))
    elif a.cmd == "rankings":
        params = {"type": a.type, "marketCountry": a.country,
                  "duration": a.duration, "count": a.count}
        if a.exclude_caution:
            params["excludeInvestmentCaution"] = "true"
        out(api("GET", "/api/v1/rankings", params))
    elif a.cmd == "exchange-rate":
        out(api("GET", "/api/v1/exchange-rate",
                {"baseCurrency": a.base, "quoteCurrency": a.quote}))
    elif a.cmd == "market-calendar":
        out(api("GET", "/api/v1/market-calendar/KR", {"date": a.date} if a.date else None))
    elif a.cmd == "index-prices":
        out(api("GET", "/api/v1/market-indicators/prices", {"symbols": a.symbols}))
    elif a.cmd == "market-flow":
        params = {"interval": a.interval, "count": a.count}
        if a.until:
            params["until"] = a.until
        out(api("GET", f"/api/v1/market-indicators/{a.symbol}/investor-trading", params))
    elif a.cmd == "flow":
        params = {"count": a.count}
        if a.until:
            params["until"] = a.until
        out(api("GET", f"/api/v1/stocks/{a.symbol}/investor-trading", params))
    elif a.cmd == "short-selling":
        params = {"count": a.count}
        if a.until:
            params["until"] = a.until
        out(api("GET", f"/api/v1/stocks/{a.symbol}/short-selling", params))
    elif a.cmd == "accounts":
        out(api("GET", "/api/v1/accounts"))
    elif a.cmd == "holdings":
        out(api("GET", "/api/v1/holdings", {"symbol": a.symbol} if a.symbol else None,
                account=True))
    elif a.cmd == "buying-power":
        out(api("GET", "/api/v1/buying-power", {"currency": a.currency}, account=True))
    elif a.cmd == "sellable":
        out(api("GET", "/api/v1/sellable-quantity", {"symbol": a.symbol}, account=True))
    elif a.cmd == "commissions":
        out(api("GET", "/api/v1/commissions", account=True))
    elif a.cmd == "orders":
        params = {"status": a.status}
        if a.symbol:
            params["symbol"] = a.symbol
        out(api("GET", "/api/v1/orders", params, account=True))
    elif a.cmd == "order-get":
        out(api("GET", f"/api/v1/orders/{a.order_id}", account=True))
    elif a.cmd == "order":
        import uuid
        req = {
            "symbol": a.symbol,
            "side": a.side.upper(),
            "orderType": "LIMIT" if a.price else "MARKET",
            "quantity": a.qty,
            "clientOrderId": str(uuid.uuid4()),  # idempotency key
        }
        if a.price:
            req["price"] = a.price
        out(api("POST", "/api/v1/orders", body=req, account=True))
    elif a.cmd == "cancel":
        out(api("POST", f"/api/v1/orders/{a.order_id}/cancel", account=True))
    else:
        p.error(f"unknown command {a.cmd}")


if __name__ == "__main__":
    main()
