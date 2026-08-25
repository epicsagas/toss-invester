#!/usr/bin/env python3
"""Domain eval for toss-investor — read-only endpoints only, NEVER orders.

Measures: indicator math correctness, live API reachability+latency, output
schema validity, plugin structure. Emits {"composite": 0..1, ...} on stdout.
Credentials come from .env (auto-loaded by toss.py) or the environment.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd, timeout=60):
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def j(*cmd, timeout=60):
    code, out, err = run(list(cmd), timeout)
    return code, (json.loads(out) if code == 0 and out.strip() else None), err


def main():
    results = {}

    # 1. indicator math self-checks (weighted 0.4)
    code, out, err = run([sys.executable, "scripts/test_indicators.py"])
    results["indicator_math"] = {"pass": code == 0,
                                 "detail": (out or err).strip().splitlines()[-1][:120]}

    # 2. live API through our wrapper (weighted 0.3) — read-only endpoints
    api_checks = {}
    for name, cmd in {
        "prices": ["python3", "scripts/toss.py", "prices", "005930"],
        "candles_1d": ["python3", "scripts/toss.py", "candles", "005930", "--interval", "1d", "--count", "200"],
        "candles_1m": ["python3", "scripts/toss.py", "candles", "005930", "--interval", "1m", "--count", "200"],
        "orderbook": ["python3", "scripts/toss.py", "orderbook", "005930"],
        "trades": ["python3", "scripts/toss.py", "trades", "005930", "--count", "5"],
    }.items():
        t0 = time.time()
        code, data, err = j(*cmd)
        api_checks[name] = {"pass": code == 0 and isinstance(data, (list, dict)),
                            "latency_ms": int((time.time() - t0) * 1000),
                            "error": err.strip()[:100] if code else None}
    results["live_api"] = api_checks

    # 3. indicator pipeline schema on live data (weighted 0.2)
    candles = subprocess.run(["python3", "scripts/toss.py", "candles", "005930", "--interval", "1d", "--count", "200"],
                             cwd=ROOT, capture_output=True, text=True, timeout=60).stdout
    ind = subprocess.run(["python3", "scripts/indicators.py"], cwd=ROOT, input=candles,
                         capture_output=True, text=True, timeout=60)
    schema_ok = False
    detail = ind.stderr.strip()[:120]
    if ind.returncode == 0:
        d = json.loads(ind.stdout)
        need = ["sma", "rsi", "macd", "bollinger", "atr", "stochastic", "trend", "returns_pct"]
        missing = [k for k in need if k not in d]
        schema_ok = not missing and 0 <= d["rsi"] <= 100 and isinstance(d["trend"]["read"], str)
        detail = f"missing={missing}"
    results["indicator_schema"] = {"pass": schema_ok, "detail": detail}

    # 4. structure: skills/agents/scripts present (weighted 0.1)
    skills = sorted(p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").exists())
    agents = sorted(p.stem for p in (ROOT / "agents").glob("*.md"))
    scripts = sorted(p.name for p in (ROOT / "scripts").glob("*.py"))
    struct_ok = (len(skills) == 7 and len(agents) == 7
                 and {"toss.py", "indicators.py", "screen.py", "backtest.py",
                      "test_indicators.py"} <= set(scripts))
    results["structure"] = {"pass": struct_ok, "skills": len(skills),
                            "agents": len(agents), "scripts": len(scripts)}

    # composite
    api_pass = sum(1 for c in api_checks.values() if c["pass"])
    avg_latency = sum(c["latency_ms"] for c in api_checks.values()) / len(api_checks)
    sub = {
        "indicator_math": 1.0 if results["indicator_math"]["pass"] else 0.0,
        "live_api": api_pass / len(api_checks),
        "indicator_schema": 1.0 if results["indicator_schema"]["pass"] else 0.0,
        "structure": 1.0 if results["structure"]["pass"] else 0.0,
    }
    composite = 0.4 * sub["indicator_math"] + 0.3 * sub["live_api"] + \
                0.2 * sub["indicator_schema"] + 0.1 * sub["structure"]
    payload = {"composite": round(composite, 3), "subscores": sub,
               "avg_api_latency_ms": round(avg_latency), **results}
    print(json.dumps(payload, ensure_ascii=False))
    sys.exit(0 if composite >= 0.9 else 1)


if __name__ == "__main__":
    main()
