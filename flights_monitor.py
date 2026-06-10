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
import io
import json
import os
import random
import re
import smtplib
import urllib.parse
from datetime import date, timedelta, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

import gspread
from google.oauth2.service_account import Credentials
from playwright.async_api import async_playwright, Browser

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Config ────────────────────────────────────────────────────────────────────
START_DATE  = date(2027, 1, 15)
END_DATE    = date(2027, 2, 15)
STAY_NIGHTS = 7

ORIGIN = "BKK"
DEST   = "NRT"

# Exclude budget carriers that contain "thai" in their name
EXCLUDE_THAI = ["vietjet", "airasia", "lion", "smile"]

GMAIL_USER         = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT          = ["kenglao2903@hotmail.com", "preeyapat.po@gmail.com"]

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


# Query name per airline — appended as "with X" so Google filters both
# legs to that carrier (same airline out and back). Must be a single word:
# multi-word names break Google's query parsing (falls back to landing page).
AIRLINE_QUERY = {"ANA": "ANA", "JAL": "JAL", "THAI": "THAI"}


def build_q_url(dep: date, ret: date, airline: str | None = None) -> str:
    q = f"Flights to {DEST} from {ORIGIN} on {dep.isoformat()} through {ret.isoformat()}"
    if airline:
        q += f" with {AIRLINE_QUERY[airline]}"
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

_RATE_LIMIT_SIGNALS = [
    "before you continue", "i'm not a robot", "captcha",
    "unusual traffic", "verify you're human", "our systems have detected",
]


async def _scrape_once(browser: Browser, gf_link: str) -> tuple[dict, bool]:
    """Returns (parsed_result, rate_limited)."""
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
                print("  ⚠️  rate-limit/CAPTCHA detected")
                return {}, True
            if re.search(r"\d+\s+results?\s+returned", body) and "THB" in body:
                break
        return parse_body(body, gf_link), False
    finally:
        await ctx.close()


async def scrape_date(browser: Browser, dep_date: date,
                      max_attempts: int = 3) -> dict[str, dict | None]:
    """One filtered query per airline so both legs are on the same carrier."""
    ret_date = dep_date + timedelta(days=STAY_NIGHTS)
    result: dict[str, dict | None] = {"ANA": None, "JAL": None, "THAI": None}

    for code in result:
        gf_link = build_q_url(dep_date, ret_date, airline=code)
        for attempt in range(1, max_attempts + 1):
            try:
                parsed, rate_limited = await _scrape_once(browser, gf_link)
                if parsed.get(code):
                    result[code] = parsed[code]
                    break
                wait = (random.uniform(45, 90) if rate_limited
                        else random.uniform(8, 15) * attempt)
                print(f"  [{dep_date}/{code}] attempt {attempt} miss → wait {wait:.0f}s")
            except Exception as exc:
                wait = random.uniform(10, 20) * attempt
                print(f"  [{dep_date}/{code}] attempt {attempt} ERROR: {exc} → wait {wait:.0f}s")
            await asyncio.sleep(wait)
        await asyncio.sleep(random.uniform(3, 7))

    return result


# ── Email ─────────────────────────────────────────────────────────────────────

# Brand colors: ANA blue, JAL red, THAI purple — used in table, chart, best box
AIRLINE_COLOR = {"ANA": "#1565c0", "JAL": "#d32f2f", "THAI": "#7b1fa2"}


def find_best(all_results: dict[date, dict]) -> dict | None:
    """Single cheapest fare across all dates and airlines."""
    best = None
    for dep, p in all_results.items():
        for code, info in p.items():
            if not info:
                continue
            if best is None or info["price"] < best["price"]:
                best = {**info, "airline": code, "dep_date": dep,
                        "ret_date": dep + timedelta(days=STAY_NIGHTS)}
    return best


def build_best_box(best: dict | None) -> str:
    if not best:
        return ""
    detail = (f"{best['dep_time']} → {best['arr_time']} ({best['duration']})"
              if best.get('dep_time') else "")
    return f"""
<div style="background:#e8f5e9;border:2px solid #1b5e20;border-radius:12px;
            padding:16px 20px;margin:16px 0">
  <div style="color:#1b5e20;font-size:13px;font-weight:bold">🏆 ช่วงที่ถูกที่สุด</div>
  <div style="font-size:28px;font-weight:900;color:#1b5e20;margin:4px 0">
    ฿{best['price']:,} <span style="font-size:16px;font-weight:700;color:{AIRLINE_COLOR[best['airline']]}">({best['airline']})</span>
  </div>
  <div style="color:#333;font-size:14px">
    🗓️ ออก <b>{best['dep_date'].strftime('%a %d %b %Y')}</b> →
    กลับ <b>{best['ret_date'].strftime('%a %d %b %Y')}</b>
  </div>
  <div style="color:#555;font-size:13px;margin-top:2px">⏱️ {detail}</div>
  <a href="{best['gf_link']}" target="_blank"
     style="display:inline-block;margin-top:10px;background:#1b5e20;color:white;
            text-decoration:none;padding:8px 16px;border-radius:8px;font-size:13px">
    ดูบน Google Flights →</a>
</div>"""


def build_html(all_results: dict[date, dict]) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M ICT")
    best_box = build_best_box(find_best(all_results))
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
                    f'<b style="color:{AIRLINE_COLOR[code]}">฿{info["price"]:,}</b><br>'
                    f'<small style="color:#555">{detail}</small> {link}</td>')

        rows += (f"<tr><td>{dep.strftime('%a %d %b')}</td>"
                 f"<td>{ret.strftime('%a %d %b')}</td>"
                 f"{cell('ANA')}{cell('JAL')}{cell('THAI')}</tr>")

    return f"""<html><body style="font-family:Arial,sans-serif;padding:20px">
<h2 style="color:#1565c0">✈️ ราคาตั๋ว BKK → NRT (ไป-กลับ 8 วัน / 7 คืน)</h2>
<p style="color:#555">ข้อมูล ณ {now} | ราคา THB ต่อคน รวมภาษี</p>
{best_box}
<h3 style="color:#1565c0;margin-top:20px">📋 ราคาทุกช่วง</h3>
<table border="1" cellpadding="8" cellspacing="0"
       style="border-collapse:collapse;font-size:13px;min-width:700px">
  <thead style="color:white"><tr>
    <th style="background:#37474f">วันออกเดินทาง</th>
    <th style="background:#37474f">วันกลับ</th>
    <th style="background:{AIRLINE_COLOR['ANA']}">ANA</th>
    <th style="background:{AIRLINE_COLOR['JAL']}">JAL</th>
    <th style="background:{AIRLINE_COLOR['THAI']}">THAI</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
<h3 style="color:#1565c0;margin-top:24px">📈 กราฟราคาตามวันออกเดินทาง</h3>
<img src="cid:pricechart" style="max-width:100%;border:1px solid #ddd;border-radius:8px">
<p style="color:#bbb;font-size:11px;margin-top:16px">ดึงข้อมูลจาก Google Flights | github actions</p>
</body></html>"""


AIRLINE_PLOT = AIRLINE_COLOR


def build_chart_png(all_results: dict[date, dict]) -> bytes | None:
    deps = sorted(all_results)
    if not deps:
        return None
    xlabels = [d.strftime("%d %b") for d in deps]
    x = list(range(len(deps)))

    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=110)
    plotted = False
    for code, color in AIRLINE_PLOT.items():
        ys = [all_results[d][code]["price"] if all_results[d].get(code) else None
              for d in deps]
        if any(v is not None for v in ys):
            ax.plot(x, ys, marker="o", label=code, color=color, linewidth=2)
            plotted = True
    if not plotted:
        plt.close(fig)
        return None

    ax.set_xticks(x)
    ax.set_xticklabels(xlabels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Price (THB)")
    ax.set_title("BKK → NRT round-trip price by departure date")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.get_yaxis().set_major_formatter(
        plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def send_email(html: str, chart_png: bytes | None):
    root = MIMEMultipart("related")
    root["Subject"] = f"✈️ BKK–NRT ราคาวันนี้ | {datetime.now().strftime('%d/%m/%Y')}"
    root["From"]    = GMAIL_USER
    root["To"]      = ", ".join(RECIPIENT)

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html, "html", "utf-8"))
    root.attach(alt)

    if chart_png:
        img = MIMEImage(chart_png, _subtype="png")
        img.add_header("Content-ID", "<pricechart>")
        img.add_header("Content-Disposition", "inline", filename="price_chart.png")
        root.attach(img)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
        srv.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        srv.sendmail(GMAIL_USER, RECIPIENT, root.as_string())
    print(f"✅ Email sent → {', '.join(RECIPIENT)}")


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
        date_idx = 0
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
            date_idx += 1
            # longer rest every 8 dates to let Google rate-limit window reset
            if date_idx % 8 == 0:
                rest = random.uniform(30, 50)
                print(f"⏸  {rest:.0f}s cooldown after {date_idx} dates")
                await asyncio.sleep(rest)
            else:
                await asyncio.sleep(random.uniform(8, 15))

        await browser.close()

    append_rows(ws, scrape_dt, sheet_rows)
    print(f"📊 {len(sheet_rows)} rows written to Google Sheets")

    try:
        chart = build_chart_png(all_results)
        send_email(build_html(all_results), chart)
    except Exception as exc:
        print(f"⚠️ Email failed (data still saved): {exc}")


if __name__ == "__main__":
    asyncio.run(main())
