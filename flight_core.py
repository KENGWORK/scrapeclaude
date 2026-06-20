#!/usr/bin/env python3
"""
Shared engine for the Google-Flights price monitors.

Holds the parts that were copy-pasted across every route script:
browser scrape + render-wait loop, rate-limit detection, the text fare
scanner, Google Sheets auth, and SMTP email. Route scripts import these
and supply only their own query / airline-selection / presentation.
"""

import asyncio
import json
import os
import random
import re
import smtplib
import urllib.parse
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from typing import Callable, Iterator

import gspread
from google.oauth2.service_account import Credentials
from playwright.async_api import async_playwright, Browser

# ── Env ─────────────────────────────────────────────────────────────────────
GMAIL_USER         = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
GOOGLE_SHEET_ID             = os.environ["GOOGLE_SHEET_ID"]

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

RATE_LIMIT_SIGNALS = [
    "before you continue", "i'm not a robot", "captcha",
    "unusual traffic", "verify you're human", "our systems have detected",
]

# Google Flights renders times/prices with U+202F / U+00A0 spaces → \s covers them
DEP_RE   = re.compile(r"^\d{1,2}:\d{2}\s*[AP]M$")
ARR_RE   = re.compile(r"^\d{1,2}:\d{2}\s*[AP]M(\+\d)?$")
DUR_RE   = re.compile(r"^\d+\s*hr(\s*\d+\s*min)?$")
PRICE_RE = re.compile(r"THB\s*([\d,]+)")
NONSTOP_RE = re.compile(r"^nonstop$", re.I)
STOPS_RE   = re.compile(r"^(\d+)\s*stop", re.I)


# ── Parsing ─────────────────────────────────────────────────────────────────

def clean(s: str) -> str:
    return s.replace(chr(0x202f), " ").replace(chr(0xa0), " ").strip()


def gf_url(query: str) -> str:
    return ("https://www.google.com/travel/flights?q="
            + urllib.parse.quote(query) + "&hl=en-US&curr=THB&gl=TH")


def iter_fares(text: str, gf_link: str) -> Iterator[tuple[str, dict]]:
    """Yield (airline_name, fare) for every dep/arr/duration/price block found.

    Routes reduce these to their own shape (fixed carriers, top-N, single filter).
    """
    lines = [clean(l) for l in text.split("\n")]
    for i in range(len(lines) - 5):
        if not (DEP_RE.match(lines[i]) and ARR_RE.match(lines[i + 2])
                and DUR_RE.match(lines[i + 4])):
            continue
        name = lines[i + 3]
        if not name or len(name) > 60:
            continue
        price = None
        stops = None  # 0 = nonstop, N = N stops, None = not detected
        for j in range(i, min(i + 12, len(lines))):
            if stops is None:
                if NONSTOP_RE.match(lines[j]):
                    stops = 0
                else:
                    sm = STOPS_RE.match(lines[j])
                    if sm:
                        stops = int(sm.group(1))
            if price is None:
                m = PRICE_RE.match(lines[j])
                if m:
                    price = int(m.group(1).replace(",", ""))
        if price is None:
            continue
        yield name, {
            "price":    price,
            "dep_time": lines[i],
            "arr_time": lines[i + 2],
            "duration": lines[i + 4],
            "stops":    stops,
            "gf_link":  gf_link,
        }


# ── Scraper ─────────────────────────────────────────────────────────────────

async def scrape_body(browser: Browser, url: str,
                      tries: int = 12, interval_ms: int = 4_000) -> tuple[str, bool]:
    """Load url, poll until results render. Returns (body_text, rate_limited).

    body_text is "" when rate-limited or nothing rendered.
    """
    ctx = await browser.new_context(
        locale="en-US", timezone_id="Asia/Bangkok", user_agent=USER_AGENT,
    )
    page = await ctx.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        body = ""
        for _ in range(tries):
            await page.wait_for_timeout(interval_ms)
            body = await page.inner_text("body")
            if any(s in body.lower() for s in RATE_LIMIT_SIGNALS):
                print("  rate-limit/CAPTCHA detected")
                return "", True
            if re.search(r"\d+\s+results?\s+returned", body) and "THB" in body:
                break
        return body, False
    finally:
        await ctx.close()


async def scrape_with_retry(browser: Browser, url: str,
                            extract: Callable[[str, str], object],
                            label: str = "", max_attempts: int = 3):
    """Retry/backoff loop around scrape_body + extract(body, url).

    extract returns the route's parsed result, or a falsy value to retry.
    Longer backoff on rate-limit. Returns the first truthy result, else None.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            body, rate_limited = await scrape_body(browser, url)
            if body:
                result = extract(body, url)
                if result:
                    return result
            wait = (random.uniform(45, 90) if rate_limited
                    else random.uniform(8, 15) * attempt)
            print(f"  [{label}] attempt {attempt} miss -> wait {wait:.0f}s")
        except Exception as exc:
            wait = random.uniform(10, 20) * attempt
            print(f"  [{label}] attempt {attempt} ERROR: {exc} -> wait {wait:.0f}s")
        await asyncio.sleep(wait)
    return None


def launch_browser(pw):
    return pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
    )


async def with_browser(run):
    """Open Playwright + a chromium browser, pass the browser to run(browser)."""
    async with async_playwright() as pw:
        browser = await launch_browser(pw)
        try:
            return await run(browser)
        finally:
            await browser.close()


# ── Google Sheets ───────────────────────────────────────────────────────────

def open_sheet(sheet_name: str, headers: list[str],
               rows: int = 10000, cols: int = 10):
    """Authorize, open the worksheet (creating it + header row if missing)."""
    creds = Credentials.from_service_account_info(
        json.loads(GOOGLE_SERVICE_ACCOUNT_JSON),
        scopes=["https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"],
    )
    sh = gspread.authorize(creds).open_by_key(GOOGLE_SHEET_ID)
    try:
        ws = sh.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(sheet_name, rows=rows, cols=cols)
    if not ws.row_values(1):
        end_col = chr(ord("A") + len(headers) - 1)
        ws.update(values=[headers], range_name=f"A1:{end_col}1")
        print("Sheet headers created")
    return ws


# ── Email ───────────────────────────────────────────────────────────────────

def send_email(subject: str, html: str, recipients,
               chart_png: bytes | None = None):
    """Send an HTML email. If chart_png is given, embed it as cid:pricechart."""
    to = recipients if isinstance(recipients, list) else [recipients]
    root = MIMEMultipart("related" if chart_png else "alternative")
    root["Subject"] = subject
    root["From"]    = GMAIL_USER
    root["To"]      = ", ".join(to)

    if chart_png:
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(html, "html", "utf-8"))
        root.attach(alt)
        img = MIMEImage(chart_png, _subtype="png")
        img.add_header("Content-ID", "<pricechart>")
        img.add_header("Content-Disposition", "inline", filename="price_chart.png")
        root.attach(img)
    else:
        root.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
        srv.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        srv.sendmail(GMAIL_USER, to, root.as_string())
    print(f"Email sent -> {', '.join(to)}")
