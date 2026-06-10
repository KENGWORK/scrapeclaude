#!/usr/bin/env python3
"""
BKK → NRT Flight Price Monitor
Airlines : ANA, JAL, Thai Airways
Dates    : Jan 15 – Feb 15 2027  (8 days / 7 nights round-trip)
Schedule : Daily 23:00 ICT via GitHub Actions
Storage  : Google Sheets (Service Account)
Data     : Google Flights ?q= URL rendered via Playwright, parsed from text
"""

import asyncio
import json
import os
import re
import smtplib
import urllib.parse
from datetime import date, timedelta, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import gspread
from google.oauth2.service_account import Credentials
from playwright.async_api import async_playwright, Browser

# ── Config ────────────────────────────────────────────────────────────────────
START_DATE  = date(2027, 1, 15)
END_DATE    = date(2027, 1, 17)   # TEST: 3 days only — expand to 2/15 after IP verified
STAY_NIGHTS = 7

ORIGIN = "BKK"
DEST   = "NRT"

# Exclude budget carriers that contain "thai" in their name
EXCLUDE_THAI = ["vietjet", "airasia", "lion", "smile"]

GMAIL_USER         = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT          = "kenglao2903@hotmail.com"

GOOGLE_SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
GOOGLE_SHEET_ID             = os.environ["GOOGLE_SHEET_ID"]

# Text-parse regexes (Google Flights uses U+202F / U+00A0 whitespace → \s covers them)
DEP_RE = re.compile(r"^\d{1,2}:\d{2}\s*[AP]M$")
ARR_RE = re.compile(r"^\d{1,2}:\d{2}\s*[AP]M(\+\d)?$")
DUR_RE = re.compile(r"^\d+\s*hr(\s*\d+\s*min)?$")
PRICE_RE = re.compile(r"THB\s*([\d,]+)")


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

    if not ws.row_values(1):
        ws.update("A1:I1", [[
            "scrape_date", "departure_date", "return_date",
            "airline", "price_thb", "dep_time", "arr_time",
            "duration", "gf_link",
        ]])
        print("📋 Sheet headers created")
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
    if n == "ana" or "all nippon" in n:
        return "ANA"
    if "jal" in n or "japan airlines" in n:
        return "JAL"
    if (n == "thai" or "thai airways" in n) and not any(x in n for x in EXCLUDE_THAI):
        return "THAI"
    return None


def clean(s: str) -> str:
    return s.replace(chr(0x202f),chr(32)).replace(chr(0xa0),chr(32)).strip()


def build_q_url(dep: date, ret: date) -> str:
    q = f"Flights to {DEST} from {ORIGIN} on {dep.isoformat()} through {ret.isoformat()}"
    return ("https://www.google.com/travel/flights?q="
            + urllib.parse.quote(q) + "&hl=en-US&curr=THB&gl=TH")


def parse_body(text: str, gf_link: str) -> dict[str, dict | None]:
    lines = [clean(l) for l in text.split("\n")]
    result: dict[str, dict | None] = {"ANA": None, "JAL": None, "THAI": None}

    for i in range(len(lines) - 5):
        if not (DEP_RE.match(lines[i]) and ARR_RE.match(lines[i + 2])
                and DUR_RE.match(lines[i + 4])):
            continue
        code = match_airline(lines[i + 3])
        if not code:
            continue
        price = None
        for j in range(i, min(i + 12, len(lines))):
            m = PRICE_RE.match(lines[j])
            if m:
                price = int(m.group(1).replace(",", ""))
                break
        if price is None:
            continue
        if result[code] is None or price < result[code]["price"]:
            result[code] = {
                "price":    price,
                "dep_time": lines[i],
                "arr_time": lines[i + 2],
                "duration": lines[i + 4],
                "gf_link":  gf_link,
            }
    return result


# ── Scraper ───────────────────────────────────────────────────────────────────

async def scrape_date(browser: Browser, dep_date: date) -> dict[str, dict | None]:
    ret_date = dep_date + timedelta(days=STAY_NIGHTS)
    gf_link = build_q_url(dep_date, ret_date)
    result: dict[str, dict | None] = {"ANA": None, "JAL": None, "THAI": None}

    ctx = await browser.new_context(
        locale="en-US",
        timezone_id="Asia/Bangkok",
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    )
    page = await ctx.new_page()
    try:
        await page.goto(gf_link, wait_until="domcontentloaded", timeout=60_000)

        # Poll until results render (text contains "results returned" + a THB price)
        for _ in range(6):
            await page.wait_for_timeout(5_000)
            body = await page.inner_text("body")
            if "results returned" in body and "THB" in body:
                break

        result = parse_body(body, gf_link)
    except Exception as exc:
        print(f"  [{dep_date}] ERROR: {exc}")
    finally:
        await ctx.close()

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

async def main():
    ws = get_worksheet()
    scrape_dt = datetime.now()
    all_results: dict[date, dict] = {}
    sheet_rows: list[dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        cur = START_DATE
        while cur <= END_DATE:
            ret = cur + timedelta(days=STAY_NIGHTS)
            print(f"⏳ {cur} ...", end=" ", flush=True)
            prices = await scrape_date(browser, cur)
            all_results[cur] = prices

            found = []
            for airline, info in prices.items():
                if info:
                    found.append(f"{airline}=฿{info['price']:,}")
                    sheet_rows.append({
                        "dep_date": cur.isoformat(), "ret_date": ret.isoformat(),
                        "airline": airline, "price": info["price"],
                        "dep_time": info["dep_time"], "arr_time": info["arr_time"],
                        "duration": info["duration"], "gf_link": info["gf_link"],
                    })
            print("  ".join(found) if found else "no match")
            cur += timedelta(days=1)

        await browser.close()

    append_rows(ws, scrape_dt, sheet_rows)
    print(f"📊 {len(sheet_rows)} rows written to Google Sheets")

    try:
        send_email(build_html(all_results))
    except Exception as exc:
        print(f"⚠️ Email failed (data still saved): {exc}")


if __name__ == "__main__":
    asyncio.run(main())
