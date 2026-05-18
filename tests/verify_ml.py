"""
Verification Suite — ML Bot Detection
======================================
Sends 10 "human-like" and 10 "bot-like" POST requests to the purchase API
endpoint and asserts that:
  • All 10 human requests pass through (HTTP 200 or 401 — NOT 403)
  • All 10 bot requests are blocked      (HTTP 403)

Usage:
    # Make sure the backend is running first:
    #   docker compose up -d   (or uvicorn app.main:app locally)
    python tests/verify_ml.py [base_url]

    Default base_url: http://localhost:8000
"""

import sys
import time
import json
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional

# ── Configuration ──────────────────────────────────────────────────────────────
BASE_URL: str = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"
PURCHASE_URL: str = f"{BASE_URL}/api/v1/purchases"

# A dummy item_id — doesn't need to exist; the middleware fires before DB lookups
DUMMY_ITEM_ID: int = 1


# ── Request profiles ───────────────────────────────────────────────────────────
@dataclass
class RequestProfile:
    label: str
    req_per_sec: float
    click_latency_ms: float
    is_mobile: int
    header_consistency: float

    def to_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "X-Req-Per-Sec":        str(self.req_per_sec),
            "X-Click-Latency-Ms":   str(self.click_latency_ms),
            "X-Is-Mobile":          str(self.is_mobile),
            "X-Header-Consistency": str(self.header_consistency),
        }


HUMAN_PROFILES: list[RequestProfile] = [
    RequestProfile("Human-01", req_per_sec=0.3,  click_latency_ms=4200.0, is_mobile=0, header_consistency=0.95),
    RequestProfile("Human-02", req_per_sec=0.8,  click_latency_ms=3100.0, is_mobile=1, header_consistency=0.98),
    RequestProfile("Human-03", req_per_sec=0.5,  click_latency_ms=5500.0, is_mobile=0, header_consistency=0.92),
    RequestProfile("Human-04", req_per_sec=1.2,  click_latency_ms=2800.0, is_mobile=1, header_consistency=0.99),
    RequestProfile("Human-05", req_per_sec=0.2,  click_latency_ms=6100.0, is_mobile=0, header_consistency=0.90),
    RequestProfile("Human-06", req_per_sec=1.0,  click_latency_ms=3900.0, is_mobile=0, header_consistency=0.96),
    RequestProfile("Human-07", req_per_sec=0.6,  click_latency_ms=4700.0, is_mobile=1, header_consistency=1.00),
    RequestProfile("Human-08", req_per_sec=0.4,  click_latency_ms=5200.0, is_mobile=0, header_consistency=0.91),
    RequestProfile("Human-09", req_per_sec=1.8,  click_latency_ms=2300.0, is_mobile=1, header_consistency=0.97),
    RequestProfile("Human-10", req_per_sec=0.7,  click_latency_ms=3750.0, is_mobile=0, header_consistency=0.93),
]

BOT_PROFILES: list[RequestProfile] = [
    RequestProfile("Bot-01",   req_per_sec=45.0, click_latency_ms=12.0,  is_mobile=0, header_consistency=0.15),
    RequestProfile("Bot-02",   req_per_sec=38.0, click_latency_ms=8.5,   is_mobile=0, header_consistency=0.22),
    RequestProfile("Bot-03",   req_per_sec=50.0, click_latency_ms=5.0,   is_mobile=0, header_consistency=0.10),
    RequestProfile("Bot-04",   req_per_sec=29.0, click_latency_ms=30.0,  is_mobile=0, header_consistency=0.28),
    RequestProfile("Bot-05",   req_per_sec=42.0, click_latency_ms=18.0,  is_mobile=0, header_consistency=0.19),
    RequestProfile("Bot-06",   req_per_sec=33.0, click_latency_ms=25.0,  is_mobile=0, header_consistency=0.32),
    RequestProfile("Bot-07",   req_per_sec=47.0, click_latency_ms=9.0,   is_mobile=0, header_consistency=0.13),
    RequestProfile("Bot-08",   req_per_sec=35.5, click_latency_ms=14.0,  is_mobile=0, header_consistency=0.20),
    RequestProfile("Bot-09",   req_per_sec=22.0, click_latency_ms=40.0,  is_mobile=0, header_consistency=0.35),
    RequestProfile("Bot-10",   req_per_sec=48.0, click_latency_ms=7.0,   is_mobile=0, header_consistency=0.08),
]


# ── HTTP helper ────────────────────────────────────────────────────────────────
def post(url: str, headers: dict, body: dict) -> tuple[int, dict]:
    """Returns (status_code, response_json)."""
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read())
        except Exception:
            return exc.code, {}
    except Exception as exc:
        print(f"  [NETWORK ERROR] {exc}")
        return 0, {}


# ── Test runner ────────────────────────────────────────────────────────────────
def run_tests() -> None:
    print(f"\n{'='*60}")
    print("  SwiftDrop — ML Bot-Detection Verification Suite")
    print(f"  Target: {PURCHASE_URL}")
    print(f"{'='*60}\n")

    body = {"item_id": DUMMY_ITEM_ID, "quantity": 1}
    passed = 0
    failed = 0
    failures: list[str] = []

    # ── Human requests: must NOT be blocked (403 = failure) ───────────────────
    print("-- Human-Like Requests (expect: 2xx or 401, NOT 403) --")
    for profile in HUMAN_PROFILES:
        status, resp = post(PURCHASE_URL, profile.to_headers(), body)
        blocked = status == 403
        ok = not blocked
        icon = "[OK]" if ok else "[FAIL]"
        print(f"  {icon} {profile.label:10s}  status={status}  "
              f"req/s={profile.req_per_sec:<5}  latency={profile.click_latency_ms}ms")
        if ok:
            passed += 1
        else:
            failed += 1
            failures.append(
                f"{profile.label}: expected NOT 403, got {status} — "
                f"bot_prob={resp.get('bot_probability', 'N/A')}"
            )
        time.sleep(0.05)

    # ── Bot requests: must be blocked (403 = success) ─────────────────────────
    print("\n-- Bot-Like Requests (expect: 403 Forbidden) --")
    for profile in BOT_PROFILES:
        status, resp = post(PURCHASE_URL, profile.to_headers(), body)
        blocked = status == 403
        ok = blocked
        icon = "[OK]" if ok else "[FAIL]"
        print(f"  {icon} {profile.label:10s}  status={status}  "
              f"req/s={profile.req_per_sec:<5}  latency={profile.click_latency_ms}ms  "
              f"bot_prob={resp.get('bot_probability', 'N/A')}")
        if ok:
            passed += 1
        else:
            failed += 1
            failures.append(
                f"{profile.label}: expected 403, got {status}"
            )
        time.sleep(0.05)

    # ── Summary ───────────────────────────────────────────────────────────────
    total = passed + failed
    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} passed")
    if failures:
        print("\n  FAILURES:")
        for f in failures:
            print(f"    • {f}")
    print(f"{'='*60}\n")

    if failed > 0:
        print("[FAIL] Verification failed — see failures above.")
        sys.exit(1)
    else:
        print("[PASS] All assertions passed. Bot detection is working correctly.")
        sys.exit(0)


if __name__ == "__main__":
    run_tests()
