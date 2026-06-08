#!/usr/bin/env python3
"""
BKK → NRT Flight Price Monitor
Airlines : ANA, JAL, Thai Airways
Dates    : Jan 15 – Feb 15 2026  (8 days / 7 nights round-trip)
Schedule : Daily 23:00 ICT via GitHub Actions
"""

import asyncio
import os
import re
import smtplib
from datetime import date, timedelta, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from playwright.async_api import async_playwright, Browser, Page

# ── Config ────────────────────────────────────────────────────────────────────
START_DATE  = date(2026, 1, 15)
END_DATE    = date(2026, 2, 15)
STAY_NIGHTS = 7          # 8 days = depart day + 7 nights

AIRLINES: dict[str, list[str]] = {
    "ANA":  ["all nippon", "ana"],
    "JAL":  ["japan airlines", "jal"],
    "THAI": ["thai airways", "การบินไทย", "thai international"],
}

GMAIL_USER        = os.environ["GMAIL_USER"]           # kenglao2909@gmail.com
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]  # Google App Password
RECIPIENT         = "kenglao2903@hotmail.com"

# ── Scraper ───────────────────────────────────────────────────────────────────

async def scrape_date(browser: Browser, dep_date: date) -> dict[str, str | None]:
    """Return {airline_code: lowest_price_str} for dep_date."""
    ret_date = dep_date + timedelta(days=STAY_NIGHTS)
    prices: dict[str, str | None] = {k: None for k in AIRLINES}

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
        # English UI + Thai region + THB currency  →  easiest to parse
        await page.goto(
            "https://www.google.com/travel/flights?hl=en&gl=TH&curr=THB",
            wait_until="domcontentloaded",
            timeout=45_000,
        )
        await page.wait_for_timeout(2_500)

        # ── Cookie banner ──
        for label in ["Accept all", "I agree"]:
            try:
                await page.get_by_role("button", name=label).click(timeout=2_000)
                await page.wait_for_timeout(600)
                break
            except Exception:
                pass

        # ── Origin ──
        await _fill_airport(page, "origin", "BKK")
        await page.wait_for_timeout(700)

        # ── Destination ──
        await _fill_airport(page, "dest", "NRT")
        await page.wait_for_timeout(700)

        # ── Dates ──
        await _set_dates(page, dep_date, ret_date)
        await page.wait_for_timeout(600)

        # ── Search ──
        try:
            await page.get_by_role("button", name=re.compile(r"Search", re.I)).click(timeout=5_000)
        except Exception:
            await page.keyboard.press("Enter")
        await page.wait_for_load_state("networkidle", timeout=35_000)
        await page.wait_for_timeout(3_500)

        # ── Parse ──
        prices = await _parse_results(page)

    except Exception as exc:
        print(f"  [{dep_date}] ERROR: {exc}")
    finally:
        await context.close()

    return prices


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
    dep_fmt = dep.strftime("%m/%d/%Y")  # 01/15/2026
    ret_fmt = ret.strftime("%m/%d/%Y")

    date_selectors = [
        ('input[aria-label*="Departure"]', 'input[aria-label*="Return"]'),
        ('input[placeholder*="Departure"]', 'input[placeholder*="Return"]'),
    ]

    for dep_sel, ret_sel in date_selectors:
        try:
            dep_input = page.locator(dep_sel).first
            await dep_input.click(timeout=3_000)
            await dep_input.triple_click()
            await dep_input.fill(dep_fmt)
            await page.wait_for_timeout(600)

            ret_input = page.locator(ret_sel).first
            await ret_input.click(timeout=3_000)
            await ret_input.triple_click()
            await ret_input.fill(ret_fmt)
            await page.wait_for_timeout(600)

            # Close date picker
            try:
                await page.get_by_role("button", name=re.compile(r"Done|ตกลง", re.I)).click(timeout=2_000)
            except Exception:
                await page.keyboard.press("Escape")
            return
        except Exception:
            continue

    raise RuntimeError("Could not set dates")


async def _parse_results(page: Page) -> dict[str, str | None]:
    prices: dict[str, str | None] = {k: None for k in AIRLINES}

    # Try multiple card selectors Google Flights uses
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
            text = (await card.inner_text()).lower()

            matched_code = None
            for code, keywords in AIRLINES.items():
                if any(kw in text for kw in keywords):
                    matched_code = code
                    break
            if not matched_code:
                continue

            # Price pattern: ฿XX,XXX or THB XX,XXX
            m = re.search(r'(?:฿|thb)\s*([\d,]+)', text)
            if not m:
                m = re.search(r'([\d,]{5,})', text)  # fallback: 5+ digit number
            if not m:
                continue

            new_val = int(m.group(1).replace(",", ""))
            price_str = f"฿{m.group(1)}"

            if prices[matched_code] is None:
                prices[matched_code] = price_str
            else:
                old_val = int(prices[matched_code].replace("฿", "").replace(",", ""))
                if new_val < old_val:
                    prices[matched_code] = price_str

        except Exception:
            continue

    return prices


# ── Email ─────────────────────────────────────────────────────────────────────

def build_html(results: dict[date, dict[str, str | None]]) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M ICT")

    rows = ""
    for dep in sorted(results):
        ret = dep + timedelta(days=STAY_NIGHTS)
        p = results[dep]

        def cell(val: str | None) -> str:
            if val:
                return f'<td style="color:#1b5e20;font-weight:bold;text-align:center">{val}</td>'
            return '<td style="color:#9e9e9e;text-align:center">–</td>'

        rows += f"""<tr>
          <td>{dep.strftime('%a %d %b %Y')}</td>
          <td>{ret.strftime('%a %d %b %Y')}</td>
          {cell(p.get('ANA'))}{cell(p.get('JAL'))}{cell(p.get('THAI'))}
        </tr>"""

    return f"""<html><body style="font-family:Arial,sans-serif;padding:20px">
<h2 style="color:#1565c0">✈️ ราคาตั๋ว BKK → NRT (ไป-กลับ 8 วัน / 7 คืน)</h2>
<p style="color:#555">ข้อมูล ณ {now} &nbsp;|&nbsp; ราคา THB ต่อคน รวมภาษี</p>
<table border="1" cellpadding="8" cellspacing="0"
       style="border-collapse:collapse;font-size:14px;min-width:600px">
  <thead style="background:#1565c0;color:white">
    <tr>
      <th>วันออกเดินทาง</th>
      <th>วันกลับ</th>
      <th>ANA</th>
      <th>JAL</th>
      <th>THAI</th>
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
    all_results: dict[date, dict] = {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
        )

        cur = START_DATE
        while cur <= END_DATE:
            print(f"⏳ {cur} ...", end=" ", flush=True)
            prices = await scrape_date(browser, cur)
            all_results[cur] = prices
            print(f"ANA={prices['ANA']}  JAL={prices['JAL']}  THAI={prices['THAI']}")
            await asyncio.sleep(4)   # polite delay between requests
            cur += timedelta(days=1)

        await browser.close()

    html = build_html(all_results)
    send_email(html)


if __name__ == "__main__":
    asyncio.run(main())
