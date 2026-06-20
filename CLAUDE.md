# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Two halves wired together by one Google Sheet:

1. **Python scrapers** (repo root) — run daily by GitHub Actions, scrape Google
   Flights round-trip prices, append rows to a Google Sheet, and email an HTML
   summary.
2. **Next.js dashboard** (`dashboard/`) — reads the same Sheet and renders price
   history/charts. Deployed on Vercel.

The Google Sheet is the database. There is no other store. Scrapers write,
dashboard reads, both authenticate with the same service-account JSON.

## Architecture

### Scrapers

`flight_core.py` is the shared engine; the three `*_monitor.py` files are thin
route scripts that import it. Keep this split — `flight_core` holds everything
that was once copy-pasted across routes:

- `scrape_body` / `scrape_with_retry` — Playwright load + render-wait poll loop,
  rate-limit/CAPTCHA detection, retry with backoff.
- `iter_fares(text, link)` — the parser. Google Flights is scraped as **rendered
  body text, not an API**. A fare is detected by line layout: a departure-time
  line, then arrival at `+2`, airline name at `+3`, duration at `+4`, price
  within the next ~12 lines. This is inherently brittle; if scraping breaks,
  suspect Google changed the page text/layout. `clean()` normalizes the U+202F /
  U+00A0 spaces Google uses.
- `open_sheet`, `send_email` — Sheets auth + SMTP. Uses gspread ≥6, whose
  `Worksheet.update` takes `(values, range_name)` order — pass them as keywords.

Each route script supplies only what genuinely differs and nothing more:

| Route | File | Worksheet | Query / selection | Output |
|-------|------|-----------|-------------------|--------|
| BKK→NRT | `flights_monitor.py` | `FlightPrices` (A:I) | one filtered query per fixed carrier (ANA/JAL/THAI) | 3-airline table + 3-line chart |
| BKK→CNX | `bkk_cnx_monitor.py` | `BKKCNXPrices` (A:I) | one query/date, top-N cheapest any carrier | top-N table + 1-line chart |
| HKT→DPS | `hkt_dps_monitor.py` | `HKTDPSPrices` (A:H) | single fixed date pair, AirAsia only | single-fare card, prev-day delta, no chart |
| BKK→CAN | `bkk_can_monitor.py` | `BKKCANPrices` (A:I) | one query/date `…nonstop`, top-N cheapest **direct** carriers | top-N table + 1-line chart |
| BKK→KIX | `bkk_kix_monitor.py` | `BKKKIXPrices` (A:I) | one query/date `…nonstop`, top-N cheapest **direct** carriers | top-N table + 1-line chart |

Direct-only routes (CAN/KIX) filter twice: the query appends `nonstop` (Google
pre-filter) and `cheapest_direct_per_airline` drops any fare `iter_fares` tags
with `stops >= 1`. `iter_fares` now yields a `stops` field (0 = nonstop, N, or
`None` when the page text didn't expose it); `None` is kept — the URL filter is
trusted when the text is silent.

The email HTML layouts are deliberately *not* shared — they differ enough that a
common builder would be more complex than three. Don't merge them.

### Dashboard

Next.js 14 App Router. `app/page.tsx` server-fetches all five worksheets in
parallel (`FlightPrices!A:I`, `BKKCNXPrices!A:I`, `HKTDPSPrices!A:H`,
`BKKCANPrices!A:I`, `BKKKIXPrices!A:I`) and passes them to
`components/RouteView.tsx` (sidebar + content layout, modal on row "ดูราคา").
CAN/KIX reuse the CNX rendering path (top-3, dynamic carriers). Charts use `recharts`. `app/api/flights/`
and `app/api/cnx/` expose the same data as JSON routes. Sheet reads are cached
1h (`revalidate = 3600`); the `FlightRecord` type in `api/flights/route.ts` is
the canonical row shape and must stay in sync with the scrapers' header lists.

## Environment

All four are required by every scraper (set as GitHub Actions secrets; the
dashboard needs the same `GOOGLE_SERVICE_ACCOUNT_JSON` + `GOOGLE_SHEET_ID` in
Vercel):

- `GMAIL_USER`, `GMAIL_APP_PASSWORD` — Gmail SMTP sender (app password, not login).
- `GOOGLE_SERVICE_ACCOUNT_JSON` — service-account credentials, raw JSON.
- `GOOGLE_SHEET_ID` — the one spreadsheet holding all three worksheets.

## Commands

Scrapers (need the env vars above; otherwise import fails immediately):

```bash
pip install -r requirements.txt
playwright install chromium          # first run only
python flights_monitor.py            # or bkk_cnx_monitor.py / hkt_dps_monitor.py

python -m py_compile flight_core.py *_monitor.py   # syntax check, no env needed
```

There is no test suite. To validate parser/selection logic without network,
exercise `flight_core.iter_fares` and a route's reduction (`match_airline`,
`cheapest_per_airline`, `cheapest_airasia`) against a synthetic body string
built with the `dep / - / arr / name / dur / - / "THB n"` line layout.

Dashboard (`cd dashboard`):

```bash
npm install
npm run dev      # local
npm run build
```

## Schedules

GitHub Actions cron in `.github/workflows/`, times in UTC (ICT = UTC+7):
`daily_flights.yml` (NRT, 16:00 & 07:00 UTC), `bkk_cnx_flights.yml` (CNX,
04:00 UTC), `hkt_dps_flights.yml` (DPS, 04:00 UTC, runs with `python -X utf8`
for the Thai text). Workflows invoke the scripts by filename — renaming a
`*_monitor.py` means updating its workflow too.

## Adding a route

New `<route>_monitor.py` that imports `flight_core`; reuse `iter_fares`,
`scrape_with_retry`, `open_sheet`, `send_email`. Add a worksheet name + header
list, a workflow yml, and (if surfacing it in the dashboard) a `fetchSheet`
range in `page.tsx`.
