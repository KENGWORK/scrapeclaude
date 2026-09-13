#!/usr/bin/env python3
"""
HKT → PVG Flight Price Monitor (Shanghai Airlines only)
Fixed trip : Depart 2026-10-31, Return 2026-11-03 (4 days / 3 nights)
Schedule   : Daily 01:00 ICT via GitHub Actions
Storage    : Google Sheets worksheet "HKTPVGPrices"
Engine     : flight_core (scrape + sheets + email shared across routes)
"""

import asyncio
from datetime import date, datetime

import flight_core as core

# ── Config ──────────────────────────────────────────────────────────────────
DEP_DATE = date(2026, 10, 31)
RET_DATE = date(2026, 11, 3)

ORIGIN, DEST = "HKT", "PVG"
RECIPIENTS = "kenglao2903@hotmail.com"
SHEET_NAME = "HKTPVGPrices"
HEADERS = ["scrape_date", "departure_date", "return_date", "airline",
           "price_thb", "dep_time", "arr_time", "duration", "gf_link"]

AIRLINE_KEY = "shanghai airlines"


def build_q_url() -> str:
    q = f"Flights to {DEST} from {ORIGIN} on {DEP_DATE.isoformat()} through {RET_DATE.isoformat()}"
    return core.gf_url(q)


# ── Scraper ─────────────────────────────────────────────────────────────────

def cheapest_shanghai_airlines(body: str, gf_link: str) -> dict | None:
    """Cheapest fare whose airline name matches Shanghai Airlines."""
    best = None
    for name, fare in core.iter_fares(body, gf_link):
        if AIRLINE_KEY not in name.lower():
            continue
        if best is None or fare["price"] < best["price"]:
            best = {**fare, "airline": name}
    return best


async def scrape(browser) -> dict | None:
    url = build_q_url()

    def extract(body, gf_link):
        return cheapest_shanghai_airlines(body, gf_link)

    return await core.scrape_with_retry(browser, url, extract, label="HKT-PVG")


# ── Email ───────────────────────────────────────────────────────────────────

def build_html(info: dict | None, prev_price: int | None) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M ICT")

    if info is None:
        body_html = f"""
<div style="background:#fff3e0;border:2px solid #e65100;border-radius:12px;padding:16px 20px">
  <div style="color:#e65100;font-size:16px;font-weight:bold">ไม่พบราคา Shanghai Airlines วันนี้</div>
  <p style="color:#555">อาจถูก rate-limit หรือไม่มีเที่ยวบิน กรุณาตรวจสอบด้วยตัวเอง</p>
  <a href="{build_q_url()}" target="_blank"
     style="display:inline-block;background:#e65100;color:white;padding:8px 16px;
            border-radius:8px;text-decoration:none;font-size:13px">
    ดูบน Google Flights ->
  </a>
</div>"""
    else:
        change = ""
        if prev_price and prev_price != info["price"]:
            diff = info["price"] - prev_price
            arrow = "&#9650;" if diff > 0 else "&#9660;"
            color = "#d32f2f" if diff > 0 else "#2e7d32"
            change = (f'<span style="font-size:14px;color:{color};margin-left:8px">'
                      f'{arrow} {abs(diff):,} THB จากเมื่อวาน</span>')

        body_html = f"""
<div style="background:#e8f5e9;border:2px solid #1b5e20;border-radius:12px;padding:16px 20px">
  <div style="color:#1b5e20;font-size:13px;font-weight:bold">&#9992; {info['airline']} HKT → PVG (ไป-กลับ)</div>
  <div style="font-size:32px;font-weight:900;color:#1b5e20;margin:6px 0">
    &#3647;{info['price']:,} {change}
  </div>
  <div style="color:#333;font-size:14px">
    ออก <b>{DEP_DATE.strftime('%a %d %b %Y')}</b> ->
    กลับ <b>{RET_DATE.strftime('%a %d %b %Y')}</b>
  </div>
  <div style="color:#555;font-size:13px;margin-top:4px">
    {info['dep_time']} -> {info['arr_time']} ({info['duration']})
  </div>
  <a href="{info['gf_link']}" target="_blank"
     style="display:inline-block;margin-top:10px;background:#1b5e20;color:white;
            text-decoration:none;padding:8px 16px;border-radius:8px;font-size:13px">
    ดูบน Google Flights ->
  </a>
</div>"""

    return f"""<html><body style="font-family:Arial,sans-serif;padding:20px">
<h2 style="color:#e65100">&#9992; HKT → PVG | Shanghai Airlines | ราคาวันนี้</h2>
<p style="color:#555;font-size:13px">ข้อมูล ณ {now} | ราคา THB ต่อคน รวมภาษี</p>
{body_html}
<p style="color:#bbb;font-size:11px;margin-top:20px">ดึงข้อมูลจาก Google Flights | github actions</p>
</body></html>"""


# ── Main ────────────────────────────────────────────────────────────────────

async def main():
    ws = core.open_sheet(SHEET_NAME, HEADERS)
    scrape_dt = datetime.now().strftime("%Y-%m-%d %H:%M")

    all_rows = ws.get_all_values()
    prev_price = None
    if len(all_rows) > 1:
        try:
            prev_price = int(all_rows[-1][4])
        except (ValueError, IndexError):
            pass

    info = await core.with_browser(scrape)

    if info:
        print(f"Found: THB {info['price']:,}  {info['airline']}  "
              f"{info['dep_time']}->{info['arr_time']} ({info['duration']})")
        ws.append_rows([[
            scrape_dt, DEP_DATE.isoformat(), RET_DATE.isoformat(),
            info["airline"], info["price"], info["dep_time"], info["arr_time"],
            info["duration"], info["gf_link"],
        ]], value_input_option="USER_ENTERED")
        print("Row written to Sheets")
    else:
        print("No result found")

    try:
        subject = f"HKT-PVG Shanghai Airlines ราคาวันนี้ | {datetime.now().strftime('%d/%m/%Y')}"
        core.send_email(subject, build_html(info, prev_price), RECIPIENTS)
    except Exception as exc:
        print(f"Email failed (data still saved): {exc}")


if __name__ == "__main__":
    asyncio.run(main())
