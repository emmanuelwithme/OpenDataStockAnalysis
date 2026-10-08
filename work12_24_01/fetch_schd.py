#!/usr/bin/env python3
"""WORK12-24-01: preserve real Schwab NAV bytes and independent Yahoo market-price candidate."""
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pandas_market_calendars as mcal
import requests
import yfinance as yf
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

NAV_URL = "https://www.schwabassetmanagement.com/sites/g/files/eyrktu361/files/product_files/SCHD/SCHD_NAV_History.CSV"
OUT = Path("work12_24_01/output")
OUT.mkdir(parents=True, exist_ok=True)
report = {
    "work": "WORK12-24-01",
    "ticker": "SCHD",
    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
    "canonical_written": False,
    "requires_bline_authorized_import": True,
    "official_nav": {"url": NAV_URL, "status": "BLOCKED", "source_version": None},
    "yahoo_market_data": {"status": "BLOCKED", "source_version": None},
    "notes": [
        "Schwab NAV and Yahoo market prices are different data series.",
        "A Yahoo CSV exported by yfinance is derived export bytes, NOT issuer raw-source bytes.",
        "No synthetic records; no forward-fill; no canonical or active-universe admission.",
        "Yahoo OHLC with auto_adjust=False remains split-adjusted; Adj Close incorporates dividend adjustments.",
    ],
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def official_nav():
    s = requests.Session()
    retry = Retry(total=3, connect=3, read=3, backoff_factor=2,
                  status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    response = s.get(NAV_URL, timeout=(15, 60),
                     headers={"User-Agent": "Mozilla/5.0 (compatible; SCHD-research-source-check/1.0)"})
    response.raise_for_status()
    raw = response.content
    probe = raw[:4000].lstrip().lower()
    if len(raw) < 4000 or raw.count(b"\n") < 30 or probe.startswith(
        (b"<!doctype", b"<html", b"<?xml")
    ):
        raise ValueError("Official NAV response is too small or resembles HTML/XML, not an NAV CSV")
    # Keep the *exact* response bytes: no Unicode transcoding, spreadsheet round-trip or reformatting.
    target = OUT / "SCHD_SCHWAB_NAV_History_RAW.CSV"
    target.write_bytes(raw)
    report["official_nav"].update({
        "status": "RAW_SOURCE_CAPTURED_NEEDS_ROW_VALIDATION",
        "raw_file": target.name,
        "bytes": len(raw),
        "sha256": sha256(raw),
        "http_status": response.status_code,
        "content_type": response.headers.get("Content-Type"),
        "etag": response.headers.get("ETag"),
        "last_modified": response.headers.get("Last-Modified"),
    })


def yahoo_candidate():
    eastern = datetime.now(ZoneInfo("America/New_York"))
    # 'end' is exclusive. Never mix an incomplete live session into the final history.
    last_full_date = eastern.date() - timedelta(days=1)
    end_exclusive = last_full_date + timedelta(days=1)
    hist = yf.Ticker("SCHD").history(
        start="2011-10-20", end=end_exclusive.isoformat(),
        interval="1d", auto_adjust=False, actions=True, repair=False
    )
    if hist.empty:
        raise ValueError("Yahoo Finance returned zero rows")
    missing_cols = sorted(set(["Open", "High", "Low", "Close", "Adj Close",
                               "Volume", "Dividends", "Stock Splits"]) - set(hist.columns))
    if missing_cols:
        raise ValueError(f"Missing required Yahoo columns: {missing_cols}")
    frame = hist.reset_index()
    if "Date" not in frame.columns:
        raise ValueError("Yahoo Date index not found")
    frame["Date"] = pd.to_datetime(frame["Date"]).dt.strftime("%Y-%m-%d")
    frame = frame[["Date", "Open", "High", "Low", "Close", "Adj Close",
                   "Volume", "Dividends", "Stock Splits"]].copy()
    if frame["Date"].duplicated().any():
        raise ValueError("Yahoo duplicated trading dates")
    if not frame["Date"].is_monotonic_increasing:
        raise ValueError("Yahoo dates not monotonic")
    if frame[["Open", "High", "Low", "Close", "Adj Close"]].isna().any().any():
        raise ValueError("Yahoo has null price values")
    if (frame[["Open", "High", "Low", "Close", "Adj Close"]] <= 0).any().any():
        raise ValueError("Yahoo has non-positive price values")
    if (frame["High"] < frame[["Open", "Low", "Close"]].max(axis=1) - 1e-6).any():
        raise ValueError("Yahoo High < Open, Low or Close")
    if (frame["Low"] > frame[["Open", "High", "Close"]].min(axis=1) + 1e-6).any():
        raise ValueError("Yahoo Low > Open, High or Close")
    if (frame["Volume"] < 0).any():
        raise ValueError("Yahoo has negative volume")
    nyse = mcal.get_calendar("NYSE")
    nyse_days = set(nyse.valid_days(start_date=frame["Date"].iloc[0],
                                    end_date=frame["Date"].iloc[-1]).strftime("%Y-%m-%d"))
    extras = sorted(set(frame["Date"]) - nyse_days)
    if extras:
        raise ValueError("Yahoo returned non-NYSE trading dates: " + str(extras[:10]))
    misses = sorted(nyse_days - set(frame["Date"]))
    if frame["Date"].iloc[-1] > last_full_date.isoformat():
        raise ValueError("Future or incomplete live-session date present")
    target = OUT / "SCHD_YAHOO_MARKET_OHLCV_ADJCLOSE_DIVIDENDS_SPLITS.csv"
    frame.to_csv(target, index=False, encoding="utf-8-sig", float_format="%.8f")
    blob = target.read_bytes()
    split_events = frame.loc[frame["Stock Splits"] != 0, ["Date", "Stock Splits"]]
    report["yahoo_market_data"].update({
        "status": "CANDIDATE_FOR_INDEPENDENT_VERIFICATION",
        "file": target.name, "rows": len(frame),
        "first_date": frame["Date"].iloc[0], "last_date": frame["Date"].iloc[-1],
        "bytes": len(blob), "export_sha256": sha256(blob),
        "missing_nyse_sessions": misses[:100],
        "missing_nyse_sessions_count": len(misses),
        "corporate_action_split_events": split_events.to_dict("records"),
        "data_class": "THIRD_PARTY_MARKET_DATA",
        "price_basis": "split-adjusted OHLC, non-dividend-adjusted when auto_adjust=False",
    })


if __name__ == "__main__":
    for label, task in [("official_nav", official_nav),
                        ("yahoo_market_data", yahoo_candidate)]:
        try:
            task()
        except Exception as exc:
            report[label]["status"] = "BLOCKED"
            report[label]["error"] = f"{type(exc).__name__}: {exc}"
            print(f"[{label}] BLOCKED: {exc}", file=sys.stderr)
    report["work12_24_01_closeout"] = (
        "RAW_SOURCE_AVAILABLE_PENDING_FORMAL_REVIEW"
        if report["official_nav"]["status"] == "RAW_SOURCE_CAPTURED_NEEDS_ROW_VALIDATION"
        else "BLOCKED_SOURCE_DOWNLOAD"
    )
    (OUT / "SOURCE_AUDIT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    # No PASS based solely on a third-party market-price export.
    sys.exit(0 if report["official_nav"]["status"].startswith("RAW_SOURCE_CAPTURED") else 2)
