"""WORK12-24-05 GitHub controlled Yahoo chart raw pilot.

This collects actual provider HTTP response bytes on the GitHub runner; it does not
approve a REAL provider, update any database, or compute performance metrics.
No downloaded market history is committed or uploaded as a public artifact.
"""
import argparse
import hashlib
import ipaddress
import json
import socket
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener

HOST = "query1.finance.yahoo.com"
PROVIDER = "YAHOO_FINANCE_CHART_V8"
MAX_BYTES = 8 * 1024 * 1024


class PilotError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise PilotError("REDIRECT_NOT_APPROVED")


def make_request(symbol, start, end):
    import re
    if not isinstance(symbol, str) or not re.fullmatch(r"[A-Za-z0-9^.=-]{1,32}", symbol):
        raise PilotError("INVALID_SYMBOL")
    try:
        a, b = date.fromisoformat(start), date.fromisoformat(end)
    except (TypeError, ValueError) as exc:
        raise PilotError("INVALID_DATE") from exc
    if a.isoformat() != start or b.isoformat() != end or a > b or b == date.max:
        raise PilotError("INVALID_DATE_WINDOW")
    p1 = int(datetime.combine(a, datetime.min.time(), tzinfo=timezone.utc).timestamp())
    p2 = int(datetime.combine(b + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).timestamp())
    params = {"period1": p1, "period2": p2, "interval": "1d",
              "events": "div,splits", "includeAdjustedClose": "true"}
    url = f'https://{HOST}/v8/finance/chart/{quote(symbol, safe="")}?{urlencode(params)}'
    return url, params


def inspect_chart(raw, symbol):
    if not raw or len(raw) > MAX_BYTES:
        raise PilotError("EMPTY_OR_TOO_LARGE")
    try:
        obj = json.loads(raw)["chart"]
        if obj.get("error") is not None:
            raise PilotError("PROVIDER_ERROR")
        items = obj["result"]
        if not isinstance(items, list) or len(items) != 1:
            raise PilotError("INVALID_RESULT_COUNT")
        result = items[0]
        if result["meta"]["symbol"].upper() != symbol.upper():
            raise PilotError("SYMBOL_MISMATCH")
        ticks = result["timestamp"]
        quotes = result["indicators"]["quote"][0]
        adj = result["indicators"]["adjclose"][0]["adjclose"]
        if not ticks or not all(type(t) is int for t in ticks):
            raise PilotError("INVALID_TIMESTAMPS")
        for field in ("open", "high", "low", "close", "volume"):
            if not isinstance(quotes.get(field), list) or len(quotes[field]) != len(ticks):
                raise PilotError("INVALID_OHLCV_SHAPE")
        if not isinstance(adj, list) or len(adj) != len(ticks):
            raise PilotError("NO_ADJUSTED_CLOSE")
        if not any(v is not None for v in quotes["close"]):
            raise PilotError("NO_PRICE_VALUES")
        if not any(v is not None for v in adj):
            raise PilotError("NO_ADJUSTED_CLOSE_VALUES")
        events = result.get("events") or {}
        dividends = events.get("dividends") or {}
        splits = events.get("splits") or {}
        if not isinstance(dividends, dict) or not isinstance(splits, dict):
            raise PilotError("INVALID_EVENT_SHAPE")
        return {"MARKET_PRICE": {"state": "PRESENT", "rows": len(ticks), "adjusted_close": True},
                "DISTRIBUTION": {"state": "PRESENT" if dividends else "DATA_INSUFFICIENT", "rows": len(dividends)},
                "CORPORATE_ACTION": {"state": "PRESENT" if splits else "DATA_INSUFFICIENT", "rows": len(splits)},
                "last_provider_timestamp_utc": datetime.fromtimestamp(max(ticks), timezone.utc).isoformat()}
    except PilotError:
        raise
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
        raise PilotError("INVALID_CHART_SHAPE") from exc


def fetch_raw(url, attempts=3):
    if not 1 <= attempts <= 4:
        raise PilotError("INVALID_RETRY")
    for attempt in range(attempts):
        try:
            addresses = socket.getaddrinfo(HOST, 443, type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):
                raise PilotError("DNS_ADDRESS_BLOCKED")
            req = Request(url, headers={"Accept": "application/json",
                                     "User-Agent": "Mozilla/5.0 (compatible; ResearchPilot/1.0)"})
            with build_opener(NoRedirect(), HTTPSHandler()).open(req, timeout=25) as response:
                if response.status != 200:
                    raise PilotError("NON_200")
                raw = response.read(MAX_BYTES + 1)
            if not raw or len(raw) > MAX_BYTES:
                raise PilotError("INVALID_RAW_SIZE")
            return raw
        except HTTPError as exc:
            code = "RATE_LIMIT" if exc.code == 429 else "HTTP_" + str(exc.code)
            retryable = exc.code in (429, 500, 502, 503, 504)
        except (OSError, TimeoutError, URLError):
            code, retryable = "NETWORK_UNAVAILABLE", True
        except PilotError as exc:
            code, retryable = str(exc), False
        if not retryable or attempt == attempts - 1:
            raise PilotError(code)
        time.sleep(min(2 ** attempt, 4))
    raise PilotError("FETCH_FAILED")


def controlled_pilot(symbol, start, end, output_dir):
    url, params = make_request(symbol, start, end)
    raw = fetch_raw(url)
    classes = inspect_chart(raw, symbol)
    raw_sha = hashlib.sha256(raw).hexdigest()
    location = Path(output_dir)
    location.mkdir(parents=True, exist_ok=True)
    raw_path = location / (raw_sha + ".raw.json")
    with raw_path.open("xb") as output:
        output.write(raw)
    if hashlib.sha256(raw_path.read_bytes()).hexdigest() != raw_sha:
        raise PilotError("RAW_SHA_MISMATCH")
    receipt = {"schema": "WORK12_24_05_YAHOO_GITHUB_CONTROLLED_PILOT_v1",
               "evidence_state": "CONTROLLED_PILOT", "real_provider_approved": False,
               "qa_ready": False, "canonical_written": False, "personal_written": False,
               "provider_id": PROVIDER, "origin_format": "PROVIDER_HTTP_RESPONSE",
               "request": {"symbol": symbol, "start": start, "end": end, "parameters": params},
               "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
               "raw_sha256": raw_sha, "raw_bytes": len(raw), "classes": classes}
    (location / (raw_sha + ".receipt.json")).write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf8")
    print("PASS: YAHOO LIVE CONTROLLED PILOT " + json.dumps(receipt, sort_keys=True))
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--start", default="2020-01-01")
    parser.add_argument("--end", default="2021-01-01")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="work12_24_05_pilot_") as tmp:
        receipt = controlled_pilot(args.symbol, args.start, args.end, tmp)
        if receipt["classes"]["MARKET_PRICE"]["state"] != "PRESENT":
            raise PilotError("PRICE_MISSING")
        if args.symbol.upper() == "AAPL" and args.start <= "2020-08-31" <= args.end:
            if receipt["classes"]["CORPORATE_ACTION"]["state"] != "PRESENT":
                raise PilotError("EXPECTED_AAPL_SPLIT_MISSING")


if __name__ == "__main__":
    try:
        main()
    except PilotError as exc:
        print("BLOCKED: YAHOO CONTROLLED PILOT: " + str(exc), file=sys.stderr)
        sys.exit(2)
