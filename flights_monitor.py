#!/usr/bin/env python3
"""
BKK → NRT Flight Price Monitor
Airlines : ANA, JAL, Thai Airways
Dates    : Jan 15 – Feb 15 2026  (8 days / 7 nights round-trip)
Schedule : Daily 23:00 ICT via GitHub Actions
Storage  : Google Sheets (Service Account)
"""

import asyncio
import json
import os
import re
import smtplib
from datetime import date, timedelta, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import gspread
from google.oauth2.service_account import Credentials
from playwright.async_api import async_playwright, Browser, Page

# ── Config ────────────────────────────────────────────────────────────────────
START_DATE  = date(2026, 1, 15)
END_DATE    = date(2026, 2, 15)
STAY_NIGHTS = 7

AIRLINES: dict[str, list[str]] = {
    "ANA":  ["all nippon", "ana"],
    "JAL":  ["japan airlines", "jal"],
    "THAI": ["thai airways", "การบินไทย", "thai international"],
}

GMAIL_USER         = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT          = "kenglao2903@hotmail.com"

GOOGLE_SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
GOOGLE_SHEET_ID             = os.environ.get("GOOGLE_SHEET_ID", "")

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

    if GOOGLE_SHEET_ID:
        sh = gc.open_by_key(GOOGLE_SHEET_ID)
    else:
        sh = gc.create("BKK-NRT Flight Prices")
        sh.share(None, perm_type="anyone", role="reader")
        print(f"📊 New sheet created: {sh.id}  ← save as GOOGLE_SHEET_ID secret")

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

    return ws


def append_rows(ws, scrape_dt: datetime, rows: list[dict]):
    data = []
    for r in rows:
        data.append([
            scrape_dt.strftime("%Y-%m-%d %H:%M"),
            r["dep_date"],
            r["ret_date"],
            r["airline"],
            r["price"],
            r.get("dep_time", ""),
            r.get("arr_time", ""),
            r.get("duration", ""),
            r.get("gf_link", ""),
        ])
    if data:
        ws.append_rows(data, value_input_option="USER_ENTERED")


# ── Scraper ───────────────────────────────────────────────────────────────────

FlightInfo = dict  # {price, dep_time, arr_time, duration, gf_link} | None


async def scrape_date(browser: Browser, dep_date: date) -> dict[str, FlightInfo | None]:
    ret_date = dep_date + timedelta(days=STAY_NIGHTS)
    result: dict[str, FlightInfo | None] = {k: None for k in AIRLINES}

    context = await browser.new_context(
        locale="en-US",
        timezone_id="Asia/Bangkok",
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    page = await context.new_page()

    try:
        await page.goto(
            "https://www.google.com/travel/flights?hl=en&gl=TH&curr=THB",
            wait_until="domcontentloaded",
            timeout=45_000,
        )
        await page.wait_for_timeout(2_500)

        for label in ["Accept all", "I agree"]:
            try:
                await page.get_by_role("button", name=label).click(timeout=2_000)
                await page.wait_for_timeout(500)
                break
            except Exception:
                pass

        await _fill_airport(page, "origin", "BKK")
        await page.wait_for_timeout(700)
        await _fill_airport(page, "dest", "NRT")
        await page.wait_for_timeout(700)
        await _set_dates(page, dep_date, ret_date)
        await page.wait_for_timeout(500)

        try:
            await page.get_by_role("button", name=re.compile(r"Search", re.I)).click(timeout=5_000)
        except Exception:
            await page.keyboard.press("Enter")

        await page.wait_for_load_state("networkidle", timeout=35_000)
        await page.wait_for_timeout(3_500)

        gf_link = page.url
        result = await _parse_results(page, gf_link)

    except Exception as exc:
        print(f"  [{dep_date}] ERROR: {exc}")
    finally:
        await context.close()

    return result


async def _fill_airport(page: Page, field: str, code: str):
    selectors = {
        "origin": [
            'input[aria-label*="Where from"]',
            'input[aria-label*="Origin"]',
            'input[placeholder*="Where from"]',
        ],
        "dest": [
            'input[aria-label*="Where to"]',
            'input[aria-label*="Destination"]',
            'input[placeholder*="Where to"]',
        ],
    }
    for sel in selectors[field]:
        try:
            loc = page.locator(sel).first
            await loc.click(timeout=3_000)
            await loc.triple_click()
            await loc.type(code, delay=80)
            await page.wait_for_timeout(1_500)
            await page.locator('[role="option"]').first.click(timeout=3_000)
            return
        except Exception:
            continue
    raise RuntimeError(f"Could not fill {field} with {code}")


async def _set_dates(page: Page, dep: date, ret: date):
    dep_fmt = dep.strftime("%m/%d/%Y")
    ret_fmt = ret.strftime("%m/%d/%Y")

    pairs = [
        ('input[aria-label*="Departure date"]', 'input[aria-label*="Return date"]'),
        ('input[aria-label*="Departure"]',       'input[aria-label*="Return"]'),
        ('input[placeholder*="Departure"]',      'input[placeholder*="Return"]'),
    ]
    for dep_sel, ret_sel in pairs:
        try:
            dep_in = page.locator(dep_sel).first
            await dep_in.click(timeout=3_000)
            await dep_in.triple_click()
            await dep_in.fill(dep_fmt)
            await page.wait_for_timeout(500)

            ret_in = page.locator(ret_sel).first
            await ret_in.click(timeout=3_000)
            await ret_in.triple_click()
            await ret_in.fill(ret_fmt)
            await page.wait_for_timeout(500)

            try:
                await page.get_by_role("button", name=re.compile(r"Done", re.I)).click(timeout=2_000)
            except Exception:
                await page.keyboard.press("Escape")
            return
        except Exception:
            continue
    raise RuntimeError("Could not set dates")


async def _parse_results(page: Page, gf_link: str) -> dict[str, FlightInfo | None]:
    result: dict[str, FlightInfo | None] = {k: None for k in AIRLINES}

    card_locators = [
        page.locator('[role="listitem"]'),
        page.locator('li[class*="pIav2d"]'),
        page.locator('[jsname="IWWDBc"]'),
    ]
    cards = []
    for loc in card_locators:
        cards = await loc.all()
        if cards:
            break

    for card in cards:
        try:
            text = await card.inner_text()
            text_lower = text.lower()

            matched = None
            for code, keywords in AIRLINES.items():
                if any(kw in text_lower for kw in keywords):
                    matched = code
                    break
            if not matched:
                continue

            # Price
            price_m = re.search(r'(?:฿|thb)\s*([\d,]+)', text_lower)
            if not price_m:
                price_m = re.search(r'([\d,]{5,})', text)
            if not price_m:
                continue

            price_num = int(price_m.group(1).replace(",", ""))

            # Times: "09:00 – 17:30+1" or "9:00 AM – 5:30 PM"
            time_m = re.search(
                r'(\d{1,2}:\d{2}(?:\s*[AP]M)?)\s*[–\-]\s*(\d{1,2}:\d{2}(?:\+\d)?(?:\s*[AP]M)?)',
                text,
            )
            dep_time = time_m.group(1).strip() if time_m else ""
            arr_time = time_m.group(2).strip() if time_m else ""

            # Duration: "7 hr 30 min" or "7 ชม. 30 น."
            dur_m = re.search(
                r'(\d+)\s*(?:hr|ชม)[.\s]*(\d+)?\s*(?:min|น)?',
                text,
                re.IGNORECASE,
            )
            if dur_m:
                h = dur_m.group(1)
                m = dur_m.group(2) or "0"
                duration = f"{h}h{m}m"
            else:
                duration = ""

            info: FlightInfo = {
                "price":    price_num,
                "dep_time": dep_time,
                "arr_time": arr_time,
                "duration": duration,
                "gf_link":  gf_link,
            }

            if result[matched] is None or price_num < result[matched]["price"]:
                result[matched] = info

        except Exception:
            continue

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
            price_fmt = f"฿{info['price']:,}"
            detail = f"{info['dep_time']}→{info['arr_time']} ({info['duration']})" if info['dep_time'] else ""
            link = f'<a href="{info["gf_link"]}" target="_blank">🔗</a>' if info.get("gf_link") else ""
            return (
                f'<td style="text-align:center">'
                f'<b style="color:#1b5e20">{price_fmt}</b><br>'
                f'<small style="color:#555">{detail}</small> {link}'
                f'</td>'
            )

        rows += f"""<tr>
          <td>{dep.strftime('%a %d %b %Y')}</td>
          <td>{ret.strftime('%a %d %b %Y')}</td>
          {cell('ANA')}{cell('JAL')}{cell('THAI')}
        </tr>"""

    return f"""<html><body style="font-family:Arial,sans-serif;padding:20px">
<h2 style="color:#1565c0">✈️ ราคาตั๋ว BKK → NRT (ไป-กลับ 8 วัน / 7 คืน)</h2>
<p style="color:#555">ข้อมูล ณ {now} | ราคา THB ต่อคน รวมภาษี</p>
<table border="1" cellpadding="8" cellspacing="0"
       style="border-collapse:collapse;font-size:13px;min-width:700px">
  <thead style="background:#1565c0;color:white">
    <tr>
      <th>วันออกเดินทาง</th><th>วันกลับ</th>
      <th>ANA</th><th>JAL</th><th>THAI</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
<p style="color:#bbb;font-size:11px;margin-top:16px">
  ดึงข้อมูลจาก Google Flights อัตโนมัติ | github actions
</p>
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

            for airline, info in prices.items():
                if info:
                    print(f"{airline}=฿{info['price']:,}({info['duration']})", end="  ")
                    sheet_rows.append({
                        "dep_date": cur.isoformat(),
                        "ret_date": ret.isoformat(),
                        "airline":  airline,
                        "price":    info["price"],
                        "dep_time": info.get("dep_time", ""),
                        "arr_time": info.get("arr_time", ""),
                        "duration": info.get("duration", ""),
                        "gf_link":  info.get("gf_link", ""),
                    })
            print()
            await asyncio.sleep(4)
            cur += timedelta(days=1)

        await browser.close()

    # Write all rows to sheet in one batch
    append_rows(ws, scrape_dt, sheet_rows)
    print(f"📊 {len(sheet_rows)} rows written to Google Sheets")

    html = build_html(all_results)
    send_email(html)


if __name__ == "__main__":
    asyncio.run(main())
