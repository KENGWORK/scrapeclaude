#!/usr/bin/env python3
"""
BKK → NRT Flight Price Monitor
Airlines : ANA, JAL, Thai Airways
Dates    : Jan 15 – Feb 15 2026  (8 days / 7 nights round-trip)
Schedule : Daily 23:00 ICT via GitHub Actions
Storage  : Google Sheets (Service Account)
Data     : fast-flights (Google Flights protobuf, no browser)
"""

import json
import os
import smtplib
import time
import urllib.parse
from datetime import date, timedelta, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import gspread
from google.oauth2.service_account import Credentials
from fast_flights import FlightData, Passengers, get_flights

# ── Config ────────────────────────────────────────────────────────────────────
START_DATE  = date(2026, 1, 15)
END_DATE    = date(2026, 2, 15)
STAY_NIGHTS = 7

ORIGIN = "BKK"
DEST   = "NRT"

# Match airline names returned by Google Flights → our short codes
AIRLINE_MATCH: dict[str, list[str]] = {
    "ANA":  ["ana", "all nippon"],
    "JAL":  ["jal", "japan airlines"],
    "THAI": ["thai airways", "thai airasia", "thai"],
}

GMAIL_USER         = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT          = "kenglao2903@hotmail.com"

GOOGLE_SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
GOOGLE_SHEET_ID             = os.environ["GOOGLE_SHEET_ID"]


# ── Google Sheets ─────────────────────────────────────────────────────────────

def get_worksheet():
    creds_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(GOOGLE_SHEET_ID)

    try:
        ws = sh.worksheet("FlightPrices")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet("FlightPrices", rows=10000, cols=10)
        ws.append_row([
            "scrape_date", "departure_date", "return_date",
            "airline", "price_thb", "dep_time", "arr_time",
            "duration", "gf_link",
        ])
        print("📋 Sheet headers created")

    # Ensure header exists even if sheet pre-made empty
    if not ws.row_values(1):
        ws.update("A1:I1", [[
            "scrape_date", "departure_date", "return_date",
            "airline", "price_thb", "dep_time", "arr_time",
            "duration", "gf_link",
        ]])

    return ws


def append_rows(ws, scrape_dt: datetime, rows: list[dict]):
    data = [[
        scrape_dt.strftime("%Y-%m-%d %H:%M"),
        r["dep_date"], r["ret_date"], r["airline"], r["price"],
        r.get("dep_time", ""), r.get("arr_time", ""),
        r.get("duration", ""), r.get("gf_link", ""),
    ] for r in rows]
    if data:
        ws.append_rows(data, value_input_option="USER_ENTERED")


# ── Helpers ───────────────────────────────────────────────────────────────────

def match_airline(name: str) -> str | None:
    n = name.lower()
    for code, keywords in AIRLINE_MATCH.items():
        if any(kw in n for kw in keywords):
            return code
    return None


def parse_price(price_str: str) -> int | None:
    """fast-flights returns '฿12,345' or '12345' style strings."""
    digits = "".join(ch for ch in str(price_str) if ch.isdigit())
    return int(digits) if digits else None


def build_gf_link(dep: date, ret: date) -> str:
    q = f"Flights to {DEST} from {ORIGIN} on {dep.isoformat()} through {ret.isoformat()}"
    return "https://www.google.com/travel/flights?q=" + urllib.parse.quote(q)


# ── Scraper ───────────────────────────────────────────────────────────────────

def scrape_date(dep_date: date) -> dict[str, dict | None]:
    ret_date = dep_date + timedelta(days=STAY_NIGHTS)
    result: dict[str, dict | None] = {k: None for k in AIRLINE_MATCH}
    gf_link = build_gf_link(dep_date, ret_date)

    try:
        res = get_flights(
            flight_data=[
                FlightData(date=dep_date.isoformat(), from_airport=ORIGIN, to_airport=DEST),
                FlightData(date=ret_date.isoformat(), from_airport=DEST, to_airport=ORIGIN),
            ],
            trip="round-trip",
            seat="economy",
            passengers=Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0),
            fetch_mode="fallback",
        )
    except Exception as exc:
        print(f"  [{dep_date}] ERROR: {exc}")
        return result

    for f in res.flights:
        code = match_airline(getattr(f, "name", ""))
        if not code:
            continue
        price = parse_price(getattr(f, "price", ""))
        if price is None:
            continue

        info = {
            "price":    price,
            "dep_time": getattr(f, "departure", "") or "",
            "arr_time": getattr(f, "arrival", "") or "",
            "duration": getattr(f, "duration", "") or "",
            "gf_link":  gf_link,
        }
        if result[code] is None or price < result[code]["price"]:
            result[code] = info

    return result


# ── Email ─────────────────────────────────────────────────────────────────────

def build_html(all_results: dict[date, dict]) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M ICT")
    rows = ""
    for dep in sorted(all_results):
        ret = dep + timedelta(days=STAY_NIGHTS)
        p = all_results[dep]

        def cell(code: str) -> str:
            info = p.get(code)
            if not info:
                return '<td style="color:#9e9e9e;text-align:center">–</td>'
            detail = (f"{info['dep_time']}→{info['arr_time']} ({info['duration']})"
                      if info['dep_time'] else "")
            link = f'<a href="{info["gf_link"]}" target="_blank">🔗</a>'
            return (f'<td style="text-align:center">'
                    f'<b style="color:#1b5e20">฿{info["price"]:,}</b><br>'
                    f'<small style="color:#555">{detail}</small> {link}</td>')

        rows += (f"<tr><td>{dep.strftime('%a %d %b')}</td>"
                 f"<td>{ret.strftime('%a %d %b')}</td>"
                 f"{cell('ANA')}{cell('JAL')}{cell('THAI')}</tr>")

    return f"""<html><body style="font-family:Arial,sans-serif;padding:20px">
<h2 style="color:#1565c0">✈️ ราคาตั๋ว BKK → NRT (ไป-กลับ 8 วัน / 7 คืน)</h2>
<p style="color:#555">ข้อมูล ณ {now} | ราคา THB ต่อคน รวมภาษี</p>
<table border="1" cellpadding="8" cellspacing="0"
       style="border-collapse:collapse;font-size:13px;min-width:700px">
  <thead style="background:#1565c0;color:white"><tr>
    <th>วันออกเดินทาง</th><th>วันกลับ</th><th>ANA</th><th>JAL</th><th>THAI</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
<p style="color:#bbb;font-size:11px;margin-top:16px">ดึงข้อมูลจาก Google Flights | github actions</p>
</body></html>"""


def send_email(html: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"✈️ BKK–NRT ราคาวันนี้ | {datetime.now().strftime('%d/%m/%Y')}"
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
        srv.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        srv.sendmail(GMAIL_USER, RECIPIENT, msg.as_string())
    print(f"✅ Email sent → {RECIPIENT}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ws = get_worksheet()
    scrape_dt = datetime.now()
    all_results: dict[date, dict] = {}
    sheet_rows: list[dict] = []

    cur = START_DATE
    while cur <= END_DATE:
        ret = cur + timedelta(days=STAY_NIGHTS)
        print(f"⏳ {cur} ...", end=" ", flush=True)
        prices = scrape_date(cur)
        all_results[cur] = prices

        found = []
        for airline, info in prices.items():
            if info:
                found.append(f"{airline}=฿{info['price']:,}")
                sheet_rows.append({
                    "dep_date": cur.isoformat(), "ret_date": ret.isoformat(),
                    "airline":  airline, "price": info["price"],
                    "dep_time": info["dep_time"], "arr_time": info["arr_time"],
                    "duration": info["duration"], "gf_link": info["gf_link"],
                })
        print("  ".join(found) if found else "no match")

        time.sleep(2)
        cur += timedelta(days=1)

    append_rows(ws, scrape_dt, sheet_rows)
    print(f"📊 {len(sheet_rows)} rows written to Google Sheets")

    # Email failure must NOT discard scraped data (already saved above)
    try:
        send_email(build_html(all_results))
    except Exception as exc:
        print(f"⚠️ Email failed (data still saved): {exc}")


if __name__ == "__main__":
    main()
