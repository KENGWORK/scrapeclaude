#!/usr/bin/env python3
"""
HKT → DPS Flight Price Monitor (AirAsia)
Fixed trip : Depart 2026-09-01, Return 2026-09-09 (8 days / 7 nights)
Schedule   : Daily 11:00 ICT via GitHub Actions
Storage    : Google Sheets (worksheet "HKTDPSPrices")
"""

import asyncio
import json
import os
import random
import re
import smtplib
import urllib.parse
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import gspread
from google.oauth2.service_account import Credentials
from playwright.async_api import async_playwright, Browser

# ── Config ────────────────────────────────────────────────────────────────────
DEP_DATE = date(2026, 9, 1)
RET_DATE = date(2026, 9, 9)

ORIGIN = "HKT"
DEST   = "DPS"

GMAIL_USER         = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENTS         = ["kenglao2903@hotmail.com", "Sanamjang2000@hotmail.com"]

GOOGLE_SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
GOOGLE_SHEET_ID             = os.environ["GOOGLE_SHEET_ID"]

SHEET_NAME  = "HKTDPSPrices"
AIRLINE_KEY = "Indonesia AirAsia"

# Text-parse regexes
DEP_RE   = re.compile(r"^\d{1,2}:\d{2}\s*[AP]M$")
ARR_RE   = re.compile(r"^\d{1,2}:\d{2}\s*[AP]M(\+\d)?$")
DUR_RE   = re.compile(r"^\d+\s*hr(\s*\d+\s*min)?$")
PRICE_RE = re.compile(r"THB\s*([\d,]+)")

_RATE_LIMIT_SIGNALS = [
    "before you continue", "i'm not a robot", "captcha",
    "unusual traffic", "verify you're human", "our systems have detected",
]

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
        ws = sh.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(SHEET_NAME, rows=5000, cols=10)
    if not ws.row_values(1):
        ws.update([[
            "scrape_date", "departure_date", "return_date",
            "airline", "price_thb", "dep_time", "arr_time", "duration",
        ]], "A1:H1")
        print("Sheet headers created")
    return ws


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean(s: str) -> str:
    return s.replace(chr(0x202f), " ").replace(chr(0xa0), " ").strip()


def build_q_url() -> str:
    q = ("Flights to Bali from Phuket "
         f"on {DEP_DATE.isoformat()} through {RET_DATE.isoformat()}")
    return ("https://www.google.com/travel/flights?q="
            + urllib.parse.quote(q) + "&hl=en-US&curr=THB&gl=TH")


def parse_body(text: str, gf_link: str) -> dict | None:
    lines = [clean(l) for l in text.split("\n")]
    best = None
    airlines_found = []
    for i in range(len(lines) - 5):
        if not (DEP_RE.match(lines[i]) and ARR_RE.match(lines[i + 2])
                and DUR_RE.match(lines[i + 4])):
            continue
        name = lines[i + 3]
        airlines_found.append(name)
        if "airasia" not in name.lower():
            continue
        price = None
        for j in range(i, min(i + 12, len(lines))):
            m = PRICE_RE.match(lines[j])
            if m:
                price = int(m.group(1).replace(",", ""))
                break
        if price is None:
            continue
        if best is None or price < best["price"]:
            best = {
                "price":    price,
                "dep_time": lines[i],
                "arr_time": lines[i + 2],
                "duration": lines[i + 4],
                "gf_link":  gf_link,
            }
    if not best and airlines_found:
        print(f"  Airlines found (no AirAsia): {set(airlines_found)}")
    return best


# ── Scraper ───────────────────────────────────────────────────────────────────

async def _scrape_once(browser: Browser, gf_link: str) -> tuple[dict | None, bool]:
    ctx = await browser.new_context(
        locale="en-US",
        timezone_id="Asia/Bangkok",
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    )
    page = await ctx.new_page()
    try:
        await page.goto(gf_link, wait_until="domcontentloaded", timeout=60_000)
        body = ""
        for _ in range(12):
            await page.wait_for_timeout(4_000)
            body = await page.inner_text("body")
            b_low = body.lower()
            if any(s in b_low for s in _RATE_LIMIT_SIGNALS):
                print("  rate-limit/CAPTCHA detected")
                return None, True
            if re.search(r"\d+\s+results?\s+returned", body) and "THB" in body:
                break
        return parse_body(body, gf_link), False
    finally:
        await ctx.close()


async def scrape(browser: Browser, max_attempts: int = 3) -> dict | None:
    gf_link = build_q_url()
    for attempt in range(1, max_attempts + 1):
        try:
            result, rate_limited = await _scrape_once(browser, gf_link)
            if result:
                return result
            wait = random.uniform(45, 90) if rate_limited else random.uniform(10, 20) * attempt
            print(f"  attempt {attempt} miss -> wait {wait:.0f}s")
        except Exception as exc:
            wait = random.uniform(10, 20) * attempt
            print(f"  attempt {attempt} ERROR: {exc} -> wait {wait:.0f}s")
        await asyncio.sleep(wait)
    return None


# ── Email ─────────────────────────────────────────────────────────────────────

def build_html(info: dict | None, prev_price: int | None) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M ICT")

    if info is None:
        body_html = """
<div style="background:#fff3e0;border:2px solid #e65100;border-radius:12px;padding:16px 20px">
  <div style="color:#e65100;font-size:16px;font-weight:bold">ไม่พบราคา AirAsia วันนี้</div>
  <p style="color:#555">อาจถูก rate-limit หรือยังไม่มีเที่ยวบิน กรุณาตรวจสอบด้วยตัวเอง</p>
  <a href="{url}" target="_blank"
     style="display:inline-block;background:#e65100;color:white;padding:8px 16px;
            border-radius:8px;text-decoration:none;font-size:13px">
    ดูบน Google Flights ->
  </a>
</div>""".format(url=build_q_url())
    else:
        change = ""
        if prev_price and prev_price != info["price"]:
            diff = info["price"] - prev_price
            arrow = "▲" if diff > 0 else "▼"
            color = "#d32f2f" if diff > 0 else "#2e7d32"
            change = (f'<span style="font-size:14px;color:{color};margin-left:8px">'
                      f'{arrow} {abs(diff):,} THB จากเมื่อวาน</span>')

        body_html = f"""
<div style="background:#e8f5e9;border:2px solid #1b5e20;border-radius:12px;padding:16px 20px">
  <div style="color:#1b5e20;font-size:13px;font-weight:bold">✈ Indonesia AirAsia HKT → DPS (ไป-กลับ)</div>
  <div style="font-size:32px;font-weight:900;color:#1b5e20;margin:6px 0">
    ฿{info['price']:,} {change}
  </div>
  <div style="color:#333;font-size:14px">
    ออก <b>{DEP_DATE.strftime('%a %d %b %Y')}</b> →
    กลับ <b>{RET_DATE.strftime('%a %d %b %Y')}</b>
  </div>
  <div style="color:#555;font-size:13px;margin-top:4px">
    {info['dep_time']} → {info['arr_time']} ({info['duration']})
  </div>
  <a href="{info['gf_link']}" target="_blank"
     style="display:inline-block;margin-top:10px;background:#1b5e20;color:white;
            text-decoration:none;padding:8px 16px;border-radius:8px;font-size:13px">
    ดูบน Google Flights ->
  </a>
</div>"""

    return f"""<html><body style="font-family:Arial,sans-serif;padding:20px">
<h2 style="color:#e65100">✈ HKT → DPS | Indonesia AirAsia | ราคาวันนี้</h2>
<p style="color:#555;font-size:13px">ข้อมูล ณ {now} | ราคา THB ต่อคน รวมภาษี</p>
{body_html}
<p style="color:#bbb;font-size:11px;margin-top:20px">ดึงข้อมูลจาก Google Flights | github actions</p>
</body></html>"""


def send_email(html: str):
    price_label = "ราคาวันนี้"
    root = MIMEMultipart("alternative")
    root["Subject"] = f"HKT-DPS Indonesia AirAsia {price_label} | {datetime.now().strftime('%d/%m/%Y')}"
    root["From"]    = GMAIL_USER
    root["To"]      = ", ".join(RECIPIENTS)
    root.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
        srv.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        srv.sendmail(GMAIL_USER, RECIPIENTS, root.as_string())
    print(f"Email sent -> {', '.join(RECIPIENTS)}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    ws = get_worksheet()
    scrape_dt = datetime.now()

    # Get previous price for comparison
    all_rows = ws.get_all_values()
    prev_price = None
    if len(all_rows) > 1:
        try:
            prev_price = int(all_rows[-1][4])
        except (ValueError, IndexError):
            pass

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )
        print(f"Scraping HKT->DPS {DEP_DATE} / {RET_DATE} AirAsia ...")
        info = await scrape(browser)
        await browser.close()

    if info:
        print(f"Found: THB {info['price']:,}  {info['dep_time']}->{info['arr_time']} ({info['duration']})")
        ws.append_rows([[
            scrape_dt.strftime("%Y-%m-%d %H:%M"),
            DEP_DATE.isoformat(), RET_DATE.isoformat(),
            AIRLINE_KEY, info["price"],
            info["dep_time"], info["arr_time"], info["duration"],
        ]], value_input_option="USER_ENTERED")
        print("Row written to Sheets")
    else:
        print("No result found")

    try:
        send_email(build_html(info, prev_price))
    except Exception as exc:
        print(f"Email failed: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
