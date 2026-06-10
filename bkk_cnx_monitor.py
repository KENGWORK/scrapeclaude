#!/usr/bin/env python3
"""
BKK → CNX Flight Price Monitor
Dates   : Nov 20 2026 – Jan 10 2027  (5 days / 4 nights round-trip)
Airlines: Top-3 cheapest (any carrier)
Schedule: Daily 11:00 ICT via GitHub Actions
Storage : Google Sheets (worksheet "BKKCNXPrices")
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
START_DATE  = date(2026, 11, 20)
END_DATE    = date(2027,  1, 10)
STAY_NIGHTS = 4

ORIGIN = "BKK"
DEST   = "CNX"
TOP_N  = 3   # show cheapest N airlines per date

GMAIL_USER         = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT          = "kenglao2903@hotmail.com"

GOOGLE_SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
GOOGLE_SHEET_ID             = os.environ["GOOGLE_SHEET_ID"]

SHEET_NAME = "BKKCNXPrices"

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
        ws = sh.add_worksheet(SHEET_NAME, rows=10000, cols=10)
    if not ws.row_values(1):
        ws.update("A1:I1", [[
            "scrape_date", "departure_date", "return_date",
            "airline", "price_thb", "dep_time", "arr_time",
            "duration", "gf_link",
        ]])
        print("Sheet headers created")
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

def clean(s: str) -> str:
    return s.replace(chr(0x202f), chr(32)).replace(chr(0xa0), chr(32)).strip()


def build_q_url(dep: date, ret: date) -> str:
    q = f"Flights to {DEST} from {ORIGIN} on {dep.isoformat()} through {ret.isoformat()}"
    return ("https://www.google.com/travel/flights?q="
            + urllib.parse.quote(q) + "&hl=en-US&curr=THB&gl=TH")


def parse_body_all(text: str, gf_link: str) -> dict[str, dict]:
    """Return cheapest fare per airline name (any carrier)."""
    lines = [clean(l) for l in text.split("\n")]
    result: dict[str, dict] = {}

    for i in range(len(lines) - 5):
        if not (DEP_RE.match(lines[i]) and ARR_RE.match(lines[i + 2])
                and DUR_RE.match(lines[i + 4])):
            continue
        airline_name = lines[i + 3].strip()
        if not airline_name or len(airline_name) > 60:
            continue
        price = None
        for j in range(i, min(i + 12, len(lines))):
            m = PRICE_RE.match(lines[j])
            if m:
                price = int(m.group(1).replace(",", ""))
                break
        if price is None:
            continue
        if airline_name not in result or price < result[airline_name]["price"]:
            result[airline_name] = {
                "price":    price,
                "dep_time": lines[i],
                "arr_time": lines[i + 2],
                "duration": lines[i + 4],
                "gf_link":  gf_link,
            }
    return result


def top_n(all_airlines: dict[str, dict], n: int = TOP_N) -> list[tuple[str, dict]]:
    """Sorted cheapest-first, up to n airlines."""
    return sorted(all_airlines.items(), key=lambda x: x[1]["price"])[:n]


# ── Scraper ───────────────────────────────────────────────────────────────────

async def _scrape_once(browser: Browser, gf_link: str) -> tuple[dict, bool]:
    """Returns (parsed_all_airlines, rate_limited)."""
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
                return {}, True
            if re.search(r"\d+\s+results?\s+returned", body) and "THB" in body:
                break
        return parse_body_all(body, gf_link), False
    finally:
        await ctx.close()


async def scrape_date(browser: Browser, dep_date: date,
                      max_attempts: int = 3) -> list[tuple[str, dict]]:
    """Scrape all airlines for one date, return top-N cheapest."""
    ret_date = dep_date + timedelta(days=STAY_NIGHTS)
    gf_link  = build_q_url(dep_date, ret_date)

    for attempt in range(1, max_attempts + 1):
        try:
            parsed, rate_limited = await _scrape_once(browser, gf_link)
            if parsed:
                return top_n(parsed)
            wait = (random.uniform(45, 90) if rate_limited
                    else random.uniform(8, 15) * attempt)
            print(f"  [{dep_date}] attempt {attempt} miss -> wait {wait:.0f}s")
        except Exception as exc:
            wait = random.uniform(10, 20) * attempt
            print(f"  [{dep_date}] attempt {attempt} ERROR: {exc} -> wait {wait:.0f}s")
        await asyncio.sleep(wait)
    return []


# ── Email ─────────────────────────────────────────────────────────────────────

def find_best(all_results: dict[date, list]) -> dict | None:
    best = None
    for dep, ranked in all_results.items():
        if not ranked:
            continue
        airline, info = ranked[0]   # cheapest for this date
        if best is None or info["price"] < best["price"]:
            best = {**info, "airline": airline, "dep_date": dep,
                    "ret_date": dep + timedelta(days=STAY_NIGHTS)}
    return best


def build_best_box(best: dict | None) -> str:
    if not best:
        return ""
    detail = (f"{best['dep_time']} -> {best['arr_time']} ({best['duration']})"
              if best.get("dep_time") else "")
    return f"""
<div style="background:#e8f5e9;border:2px solid #1b5e20;border-radius:12px;
            padding:16px 20px;margin:16px 0">
  <div style="color:#1b5e20;font-size:13px;font-weight:bold">&#127942; ช่วงที่ถูกที่สุด</div>
  <div style="font-size:28px;font-weight:900;color:#1b5e20;margin:4px 0">
    &#3647;{best['price']:,}
    <span style="font-size:16px;font-weight:700;color:#555">({best['airline']})</span>
  </div>
  <div style="color:#333;font-size:14px">
    &#128197; ออก <b>{best['dep_date'].strftime('%a %d %b %Y')}</b> ->
    กลับ <b>{best['ret_date'].strftime('%a %d %b %Y')}</b>
  </div>
  <div style="color:#555;font-size:13px;margin-top:2px">&#9203; {detail}</div>
  <a href="{best['gf_link']}" target="_blank"
     style="display:inline-block;margin-top:10px;background:#1b5e20;color:white;
            text-decoration:none;padding:8px 16px;border-radius:8px;font-size:13px">
    ดูบน Google Flights ->
  </a>
</div>"""


def build_html(all_results: dict[date, list]) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M ICT")
    best_box = build_best_box(find_best(all_results))

    rows = ""
    for dep in sorted(all_results):
        ret    = dep + timedelta(days=STAY_NIGHTS)
        ranked = all_results[dep]

        cells = ""
        for rank, (airline, info) in enumerate(ranked):
            medal = ["&#127947;", "&#129352;", "&#129353;"][rank] if rank < 3 else ""
            detail = (f"{info['dep_time']}->{info['arr_time']} ({info['duration']})"
                      if info.get("dep_time") else "")
            link = f'<a href="{info["gf_link"]}" target="_blank">&#128279;</a>'
            cells += (f'<td style="padding:6px 10px;vertical-align:top">'
                      f'{medal} <b style="color:#1565c0">&#3647;{info["price"]:,}</b> '
                      f'<span style="color:#555;font-size:12px">{airline}</span><br>'
                      f'<small style="color:#777">{detail}</small> {link}</td>')

        # pad empty cells if fewer than TOP_N
        for _ in range(TOP_N - len(ranked)):
            cells += '<td style="color:#bbb;text-align:center;padding:6px 10px">–</td>'

        rows += (f"<tr><td style='padding:6px 10px'>{dep.strftime('%a %d %b')}</td>"
                 f"<td style='padding:6px 10px'>{ret.strftime('%a %d %b')}</td>"
                 f"{cells}</tr>")

    hdrs = "".join(
        f'<th style="background:#37474f;color:white;padding:8px 10px">&#127775; อันดับ {i+1}</th>'
        for i in range(TOP_N)
    )

    return f"""<html><body style="font-family:Arial,sans-serif;padding:20px">
<h2 style="color:#1565c0">&#9992;&#65039; ราคาตั๋ว BKK -> CNX (ไป-กลับ 5 วัน / 4 คืน)</h2>
<p style="color:#555">ข้อมูล ณ {now} | ราคา THB ต่อคน รวมภาษี | แสดง 3 สายการบินถูกสุดต่อวัน</p>
{best_box}
<h3 style="color:#1565c0;margin-top:20px">&#128203; ราคาทุกช่วง</h3>
<table border="1" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;font-size:13px;min-width:700px">
  <thead><tr>
    <th style="background:#37474f;color:white;padding:8px 10px">วันออกเดินทาง</th>
    <th style="background:#37474f;color:white;padding:8px 10px">วันกลับ</th>
    {hdrs}
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
<h3 style="color:#1565c0;margin-top:24px">&#128200; กราฟราคาอันดับ 1 ตามวันออกเดินทาง</h3>
<img src="cid:pricechart" style="max-width:100%;border:1px solid #ddd;border-radius:8px">
<p style="color:#bbb;font-size:11px;margin-top:16px">ดึงข้อมูลจาก Google Flights | github actions</p>
</body></html>"""


def build_chart_png(all_results: dict[date, list]) -> bytes | None:
    deps = sorted(all_results)
    if not deps:
        return None
    xlabels = [d.strftime("%d %b") for d in deps]
    x = list(range(len(deps)))
    ys = [all_results[d][0][1]["price"] if all_results[d] else None for d in deps]
    if not any(v is not None for v in ys):
        return None

    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=110)
    ax.plot(x, ys, marker="o", color="#1565c0", linewidth=2, label="ถูกสุดแต่ละวัน")
    ax.set_xticks(x)
    ax.set_xticklabels(xlabels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Price (THB)")
    ax.set_title("BKK -> CNX round-trip cheapest price by departure date")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def send_email(html: str, chart_png: bytes | None):
    root = MIMEMultipart("related")
    root["Subject"] = f"BKK-CNX ราคาวันนี้ | {datetime.now().strftime('%d/%m/%Y')}"
    root["From"]    = GMAIL_USER
    root["To"]      = RECIPIENT

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
    print(f"Email sent -> {RECIPIENT}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    ws = get_worksheet()
    scrape_dt = datetime.now()
    all_results: dict[date, list] = {}
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
            print(f"Scraping {cur} ...", end=" ", flush=True)
            ranked = await scrape_date(browser, cur)
            all_results[cur] = ranked

            if ranked:
                summary = " | ".join(f"{a}=THB{i['price']:,}" for a, i in ranked)
                print(summary)
                for airline, info in ranked:
                    sheet_rows.append({
                        "dep_date": cur.isoformat(), "ret_date": ret.isoformat(),
                        "airline": airline, "price": info["price"],
                        "dep_time": info["dep_time"], "arr_time": info["arr_time"],
                        "duration": info["duration"], "gf_link": info["gf_link"],
                    })
            else:
                print("no results")

            cur += timedelta(days=1)
            date_idx += 1
            if date_idx % 8 == 0:
                rest = random.uniform(25, 40)
                print(f"cooldown {rest:.0f}s")
                await asyncio.sleep(rest)
            else:
                await asyncio.sleep(random.uniform(6, 12))

        await browser.close()

    append_rows(ws, scrape_dt, sheet_rows)
    print(f"{len(sheet_rows)} rows written to Sheets")

    try:
        chart = build_chart_png(all_results)
        send_email(build_html(all_results), chart)
    except Exception as exc:
        print(f"Email failed (data still saved): {exc}")


if __name__ == "__main__":
    asyncio.run(main())
