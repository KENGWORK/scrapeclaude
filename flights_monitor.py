#!/usr/bin/env python3
"""
BKK → NRT Flight Price Monitor
Airlines : ANA, JAL, Thai Airways (fixed carriers, one filtered query each)
Dates    : Jan 15 – Feb 15 2027  (8 days / 7 nights round-trip)
Schedule : Daily 01:00 ICT via GitHub Actions
Storage  : Google Sheets worksheet "FlightPrices"
Engine   : flight_core (scrape + sheets + email shared across routes)
"""

import asyncio
import io
import random
from datetime import date, timedelta, datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import flight_core as core

# ── Config ──────────────────────────────────────────────────────────────────
START_DATE  = date(2027, 1, 15)
END_DATE    = date(2027, 2, 15)
STAY_NIGHTS = 7

ORIGIN, DEST = "BKK", "NRT"
RECIPIENTS = ["kenglao2903@hotmail.com", "preeyapat.po@gmail.com"]
SHEET_NAME = "FlightPrices"
HEADERS = ["scrape_date", "departure_date", "return_date", "airline",
           "price_thb", "dep_time", "arr_time", "duration", "gf_link"]

CARRIERS = ["ANA", "JAL", "THAI"]
AIRLINE_COLOR = {"ANA": "#1565c0", "JAL": "#d32f2f", "THAI": "#7b1fa2"}
# Budget carriers whose names also contain "thai" — must not match THAI
EXCLUDE_THAI = ["vietjet", "airasia", "lion", "smile"]


def match_airline(name: str) -> str | None:
    n = name.lower()
    if n == "ana" or "all nippon" in n:
        return "ANA"
    if "jal" in n or "japan airlines" in n:
        return "JAL"
    if (n == "thai" or "thai airways" in n) and not any(x in n for x in EXCLUDE_THAI):
        return "THAI"
    return None


def build_q_url(dep: date, ret: date, airline: str) -> str:
    # "with <AIRLINE>" filters both legs to that carrier. Single-word names only;
    # multi-word names break Google's query parsing.
    q = (f"Flights to {DEST} from {ORIGIN} "
         f"on {dep.isoformat()} through {ret.isoformat()} with {airline}")
    return core.gf_url(q)


# ── Scraper ─────────────────────────────────────────────────────────────────

async def scrape_date(browser, dep_date: date) -> dict[str, dict | None]:
    """One filtered query per carrier so both legs stay on the same airline."""
    ret_date = dep_date + timedelta(days=STAY_NIGHTS)
    result: dict[str, dict | None] = {c: None for c in CARRIERS}

    for code in CARRIERS:
        url = build_q_url(dep_date, ret_date, code)

        def extract(body, gf_link, _code=code):
            best = None
            for name, fare in core.iter_fares(body, gf_link):
                if match_airline(name) != _code:
                    continue
                if best is None or fare["price"] < best["price"]:
                    best = fare
            return best

        result[code] = await core.scrape_with_retry(
            browser, url, extract, label=f"{dep_date}/{code}")
        await asyncio.sleep(random.uniform(3, 7))
    return result


# ── Email ───────────────────────────────────────────────────────────────────

def find_best(all_results: dict[date, dict]) -> dict | None:
    best = None
    for dep, p in all_results.items():
        for code, info in p.items():
            if info and (best is None or info["price"] < best["price"]):
                best = {**info, "airline": code, "dep_date": dep,
                        "ret_date": dep + timedelta(days=STAY_NIGHTS)}
    return best


def build_best_box(best: dict | None) -> str:
    if not best:
        return ""
    detail = (f"{best['dep_time']} → {best['arr_time']} ({best['duration']})"
              if best.get("dep_time") else "")
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
                      if info["dep_time"] else "")
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


def build_chart_png(all_results: dict[date, dict]) -> bytes | None:
    deps = sorted(all_results)
    if not deps:
        return None
    x = list(range(len(deps)))
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=110)
    plotted = False
    for code, color in AIRLINE_COLOR.items():
        ys = [all_results[d][code]["price"] if all_results[d].get(code) else None
              for d in deps]
        if any(v is not None for v in ys):
            ax.plot(x, ys, marker="o", label=code, color=color, linewidth=2)
            plotted = True
    if not plotted:
        plt.close(fig)
        return None

    ax.set_xticks(x)
    ax.set_xticklabels([d.strftime("%d %b") for d in deps],
                       rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Price (THB)")
    ax.set_title("BKK → NRT round-trip price by departure date")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


# ── Main ────────────────────────────────────────────────────────────────────

async def run(browser):
    all_results: dict[date, dict] = {}
    sheet_rows: list[list] = []
    scrape_dt = datetime.now().strftime("%Y-%m-%d %H:%M")

    cur, date_idx = START_DATE, 0
    while cur <= END_DATE:
        ret = cur + timedelta(days=STAY_NIGHTS)
        print(f"⏳ {cur} ...", end=" ", flush=True)
        prices = await scrape_date(browser, cur)
        all_results[cur] = prices

        found = []
        for airline, info in prices.items():
            if info:
                found.append(f"{airline}=฿{info['price']:,}")
                sheet_rows.append([
                    scrape_dt, cur.isoformat(), ret.isoformat(), airline,
                    info["price"], info["dep_time"], info["arr_time"],
                    info["duration"], info["gf_link"],
                ])
        print("  ".join(found) if found else "no match")

        cur += timedelta(days=1)
        date_idx += 1
        if date_idx % 8 == 0:                       # let rate-limit window reset
            rest = random.uniform(30, 50)
            print(f"⏸  {rest:.0f}s cooldown after {date_idx} dates")
            await asyncio.sleep(rest)
        else:
            await asyncio.sleep(random.uniform(8, 15))

    return all_results, sheet_rows


async def main():
    ws = core.open_sheet(SHEET_NAME, HEADERS)
    all_results, sheet_rows = await core.with_browser(run)

    if sheet_rows:
        ws.append_rows(sheet_rows, value_input_option="USER_ENTERED")
    print(f"📊 {len(sheet_rows)} rows written to Google Sheets")

    try:
        subject = f"✈️ BKK–NRT ราคาวันนี้ | {datetime.now().strftime('%d/%m/%Y')}"
        core.send_email(subject, build_html(all_results), RECIPIENTS,
                        chart_png=build_chart_png(all_results))
    except Exception as exc:
        print(f"⚠️ Email failed (data still saved): {exc}")


if __name__ == "__main__":
    asyncio.run(main())
