#!/usr/bin/env python3
"""
HKT → DPS Flight Price Monitor (Indonesia AirAsia)
Fixed trip : Depart 2026-09-01, Return 2026-09-09 (8 days / 7 nights)
Schedule   : Daily 11:00 ICT via GitHub Actions
Storage    : Google Sheets worksheet "HKTDPSPrices"
Engine     : flight_core (scrape + sheets + email shared across routes)
"""

import asyncio
from datetime import date, datetime

import flight_core as core

# ── Config ──────────────────────────────────────────────────────────────────
DEP_DATE = date(2026, 9, 1)
RET_DATE = date(2026, 9, 9)

ORIGIN, DEST = "HKT", "DPS"
RECIPIENTS = ["kenglao2903@hotmail.com", "Sanamjang2000@hotmail.com"]
SHEET_NAME  = "HKTDPSPrices"
AIRLINE_KEY = "Indonesia AirAsia"
HEADERS = ["scrape_date", "departure_date", "return_date", "airline",
           "price_thb", "dep_time", "arr_time", "duration"]


def build_q_url() -> str:
    q = ("Flights to Bali from Phuket "
         f"on {DEP_DATE.isoformat()} through {RET_DATE.isoformat()}")
    return core.gf_url(q)


def cheapest_airasia(body: str, gf_link: str) -> dict | None:
    best, seen = None, []
    for name, fare in core.iter_fares(body, gf_link):
        seen.append(name)
        if "airasia" not in name.lower():
            continue
        if best is None or fare["price"] < best["price"]:
            best = fare
    if best is None and seen:
        print(f"  Airlines found (no AirAsia): {set(seen)}")
    return best


# ── Email ───────────────────────────────────────────────────────────────────

def build_html(info: dict | None, prev_price: int | None) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M ICT")

    if info is None:
        body_html = f"""
<div style="background:#fff3e0;border:2px solid #e65100;border-radius:12px;padding:16px 20px">
  <div style="color:#e65100;font-size:16px;font-weight:bold">ไม่พบราคา AirAsia วันนี้</div>
  <p style="color:#555">อาจถูก rate-limit หรือยังไม่มีเที่ยวบิน กรุณาตรวจสอบด้วยตัวเอง</p>
  <a href="{build_q_url()}" target="_blank"
     style="display:inline-block;background:#e65100;color:white;padding:8px 16px;
            border-radius:8px;text-decoration:none;font-size:13px">
    ดูบน Google Flights -></a>
</div>"""
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
    ดูบน Google Flights -></a>
</div>"""

    return f"""<html><body style="font-family:Arial,sans-serif;padding:20px">
<h2 style="color:#e65100">✈ HKT → DPS | Indonesia AirAsia | ราคาวันนี้</h2>
<p style="color:#555;font-size:13px">ข้อมูล ณ {now} | ราคา THB ต่อคน รวมภาษี</p>
{body_html}
<p style="color:#bbb;font-size:11px;margin-top:20px">ดึงข้อมูลจาก Google Flights | github actions</p>
</body></html>"""


# ── Main ────────────────────────────────────────────────────────────────────

async def run(browser):
    print(f"Scraping HKT->DPS {DEP_DATE} / {RET_DATE} AirAsia ...")
    return await core.scrape_with_retry(
        browser, build_q_url(), cheapest_airasia, label="HKT-DPS")


async def main():
    ws = core.open_sheet(SHEET_NAME, HEADERS, rows=5000)
    scrape_dt = datetime.now().strftime("%Y-%m-%d %H:%M")

    rows = ws.get_all_values()
    prev_price = None
    if len(rows) > 1:
        try:
            prev_price = int(rows[-1][4])
        except (ValueError, IndexError):
            pass

    info = await core.with_browser(run)

    if info:
        print(f"Found: THB {info['price']:,}  "
              f"{info['dep_time']}->{info['arr_time']} ({info['duration']})")
        ws.append_rows([[
            scrape_dt, DEP_DATE.isoformat(), RET_DATE.isoformat(),
            AIRLINE_KEY, info["price"],
            info["dep_time"], info["arr_time"], info["duration"],
        ]], value_input_option="USER_ENTERED")
        print("Row written to Sheets")
    else:
        print("No result found")

    try:
        subject = (f"HKT-DPS Indonesia AirAsia ราคาวันนี้ | "
                   f"{datetime.now().strftime('%d/%m/%Y')}")
        core.send_email(subject, build_html(info, prev_price), RECIPIENTS)
    except Exception as exc:
        print(f"Email failed: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
