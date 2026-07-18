#!/usr/bin/env python3
"""
BKK → HRB Flight Price Monitor (full-service carriers only)
Airlines : Top-3 cheapest among full-service carriers (whitelist below)
Dates    : Jan 5 2027 – Feb 28 2027  (8 days / 7 nights round-trip)
Schedule : Daily 15:00 ICT via GitHub Actions
Storage  : Google Sheets worksheet "BKKHRBPrices"
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
START_DATE  = date(2027, 1, 5)
END_DATE    = date(2027, 2, 28)
STAY_NIGHTS = 7
TOP_N       = 3

ORIGIN, DEST = "BKK", "HRB"
RECIPIENTS = "kenglao2903@hotmail.com"
SHEET_NAME = "BKKHRBPrices"
HEADERS = ["scrape_date", "departure_date", "return_date", "airline",
           "price_thb", "dep_time", "arr_time", "duration", "gf_link"]

# Full-service carriers plausible on BKK-HRB (direct or via CN hub connections).
# Google Flights has no full-service/LCC flag in the page text, so we filter
# by name. Match is substring/case-insensitive against the rendered airline
# name (which sometimes concatenates codeshare names, e.g. "China Eastern").
FULL_SERVICE_AIRLINES = [
    "thai airways", "thai smile",
    "china southern", "china eastern", "air china", "xiamen air",
    "hainan airlines", "shenzhen airlines", "shandong airlines",
    "cathay pacific", "cathay", "eva air", "china airlines",
    "korean air", "asiana", "singapore airlines", "all nippon", "ana",
    "japan airlines", "jal",
]


def build_q_url(dep: date, ret: date) -> str:
    q = f"Flights to {DEST} from {ORIGIN} on {dep.isoformat()} through {ret.isoformat()}"
    return core.gf_url(q)


# ── Scraper ─────────────────────────────────────────────────────────────────

def is_full_service(name: str) -> bool:
    n = name.lower()
    return any(fs in n for fs in FULL_SERVICE_AIRLINES)


def cheapest_full_service_per_airline(body: str, gf_link: str) -> dict[str, dict]:
    """Cheapest fare per airline, keeping only full-service carriers."""
    result: dict[str, dict] = {}
    for name, fare in core.iter_fares(body, gf_link):
        if not is_full_service(name):
            continue
        if name not in result or fare["price"] < result[name]["price"]:
            result[name] = fare
    return result


async def scrape_date(browser, dep_date: date) -> list[tuple[str, dict]]:
    ret_date = dep_date + timedelta(days=STAY_NIGHTS)
    url = build_q_url(dep_date, ret_date)

    def extract(body, gf_link):
        ranked = sorted(cheapest_full_service_per_airline(body, gf_link).items(),
                        key=lambda x: x[1]["price"])[:TOP_N]
        return ranked or None

    return await core.scrape_with_retry(
        browser, url, extract, label=str(dep_date)) or []


# ── Email ───────────────────────────────────────────────────────────────────

def find_best(all_results: dict[date, list]) -> dict | None:
    best = None
    for dep, ranked in all_results.items():
        if not ranked:
            continue
        airline, info = ranked[0]
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
<div style="background:#e8eaf6;border:2px solid #283593;border-radius:12px;
            padding:16px 20px;margin:16px 0">
  <div style="color:#283593;font-size:13px;font-weight:bold">&#127942; ช่วงที่ถูกที่สุด (Full Service)</div>
  <div style="font-size:28px;font-weight:900;color:#283593;margin:4px 0">
    &#3647;{best['price']:,}
    <span style="font-size:16px;font-weight:700;color:#555">({best['airline']})</span>
  </div>
  <div style="color:#333;font-size:14px">
    &#128197; ออก <b>{best['dep_date'].strftime('%a %d %b %Y')}</b> ->
    กลับ <b>{best['ret_date'].strftime('%a %d %b %Y')}</b>
  </div>
  <div style="color:#555;font-size:13px;margin-top:2px">&#9203; {detail}</div>
  <a href="{best['gf_link']}" target="_blank"
     style="display:inline-block;margin-top:10px;background:#283593;color:white;
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
                      f'{medal} <b style="color:#283593">&#3647;{info["price"]:,}</b> '
                      f'<span style="color:#555;font-size:12px">{airline}</span><br>'
                      f'<small style="color:#777">{detail}</small> {link}</td>')
        for _ in range(TOP_N - len(ranked)):
            cells += '<td style="color:#bbb;text-align:center;padding:6px 10px">–</td>'
        rows += (f"<tr><td style='padding:6px 10px'>{dep.strftime('%a %d %b')}</td>"
                 f"<td style='padding:6px 10px'>{ret.strftime('%a %d %b')}</td>"
                 f"{cells}</tr>")

    hdrs = "".join(
        f'<th style="background:#37474f;color:white;padding:8px 10px">&#127775; อันดับ {i+1}</th>'
        for i in range(TOP_N))

    return f"""<html><body style="font-family:Arial,sans-serif;padding:20px">
<h2 style="color:#283593">&#9992;&#65039; ราคาตั๋ว BKK -> HRB (ไป-กลับ 8 วัน / 7 คืน, Full Service)</h2>
<p style="color:#555">ข้อมูล ณ {now} | ราคา THB ต่อคน รวมภาษี | แสดง 3 สายการบินถูกสุดต่อวัน (เฉพาะ Full Service)</p>
{best_box}
<h3 style="color:#283593;margin-top:20px">&#128203; ราคาทุกช่วง</h3>
<table border="1" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;font-size:13px;min-width:700px">
  <thead><tr>
    <th style="background:#37474f;color:white;padding:8px 10px">วันออกเดินทาง</th>
    <th style="background:#37474f;color:white;padding:8px 10px">วันกลับ</th>
    {hdrs}
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
<h3 style="color:#283593;margin-top:24px">&#128200; กราฟราคาอันดับ 1 ตามวันออกเดินทาง</h3>
<img src="cid:pricechart" style="max-width:100%;border:1px solid #ddd;border-radius:8px">
<p style="color:#bbb;font-size:11px;margin-top:16px">ดึงข้อมูลจาก Google Flights | github actions</p>
</body></html>"""


def build_chart_png(all_results: dict[date, list]) -> bytes | None:
    deps = sorted(all_results)
    ys = [all_results[d][0][1]["price"] if all_results[d] else None for d in deps]
    if not any(v is not None for v in ys):
        return None
    x = list(range(len(deps)))
    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=110)
    ax.plot(x, ys, marker="o", color="#283593", linewidth=2, label="ถูกสุดแต่ละวัน")
    ax.set_xticks(x)
    ax.set_xticklabels([d.strftime("%d %b") for d in deps],
                       rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Price (THB)")
    ax.set_title("BKK -> HRB full-service round-trip cheapest price by departure date")
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
    all_results: dict[date, list] = {}
    sheet_rows: list[list] = []
    scrape_dt = datetime.now().strftime("%Y-%m-%d %H:%M")

    cur, date_idx = START_DATE, 0
    while cur <= END_DATE:
        ret = cur + timedelta(days=STAY_NIGHTS)
        print(f"Scraping {cur} ...", end=" ", flush=True)
        ranked = await scrape_date(browser, cur)
        all_results[cur] = ranked

        if ranked:
            print(" | ".join(f"{a}=THB{i['price']:,}" for a, i in ranked))
            for airline, info in ranked:
                sheet_rows.append([
                    scrape_dt, cur.isoformat(), ret.isoformat(), airline,
                    info["price"], info["dep_time"], info["arr_time"],
                    info["duration"], info["gf_link"],
                ])
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

    return all_results, sheet_rows


async def main():
    ws = core.open_sheet(SHEET_NAME, HEADERS)
    all_results, sheet_rows = await core.with_browser(run)

    if sheet_rows:
        ws.append_rows(sheet_rows, value_input_option="USER_ENTERED")
    print(f"{len(sheet_rows)} rows written to Sheets")

    try:
        subject = f"BKK-HRB ราคาวันนี้ (Full Service) | {datetime.now().strftime('%d/%m/%Y')}"
        core.send_email(subject, build_html(all_results), RECIPIENTS,
                        chart_png=build_chart_png(all_results))
    except Exception as exc:
        print(f"Email failed (data still saved): {exc}")


if __name__ == "__main__":
    asyncio.run(main())
