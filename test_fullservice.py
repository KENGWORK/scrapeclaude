"""Synthetic test: full-service whitelist filter for bkk_hrb_monitor.
Run: GMAIL_USER=x GMAIL_APP_PASSWORD=x GOOGLE_SERVICE_ACCOUNT_JSON={} GOOGLE_SHEET_ID=x python -X utf8 test_fullservice.py
No network. Validates parser + is_full_service reduction.
"""
import flight_core as core
import bkk_hrb_monitor as hrb


def fare(dep, arr, name, dur, stops_line, price):
    return f"{dep}\n-\n{arr}\n{name}\n{dur}\n{stops_line}\nTHB {price}\n"


body = (
    fare("7:40 AM", "1:30 PM", "China Southern", "5 hr 50 min", "1 stop", "9,800")
    + fare("9:00 AM", "8:00 PM", "Thai AirAsia", "13 hr 0 min", "1 stop", "6,200")
    + fare("10:15 AM", "4:05 PM", "China Eastern", "5 hr 50 min", "1 stop", "8,500")
    + fare("6:00 PM", "11:50 PM", "Spring Airlines", "5 hr 50 min", "1 stop", "5,400")
    + fare("2:00 PM", "9:00 PM", "China Southern", "6 hr 10 min", "1 stop", "10,400")
)

fares = list(core.iter_fares(body, "http://x"))
print("total fares parsed:", len(fares))
for name, f in fares:
    print(f"  {name:18} THB{f['price']:>6,}")

fs = hrb.cheapest_full_service_per_airline(body, "http://x")
print("full-service cheapest per airline:")
for name, f in sorted(fs.items(), key=lambda x: x[1]["price"]):
    print(f"  {name:18} THB{f['price']:>6,}")

# Assertions
assert len(fares) == 5, "should parse 5 fares"
assert "Thai AirAsia" not in fs, "LCC must be excluded"
assert "Spring Airlines" not in fs, "LCC must be excluded"
assert fs["China Southern"]["price"] == 9800, "cheapest China Southern = 9800"
assert fs["China Eastern"]["price"] == 8500
ranked = sorted(fs.items(), key=lambda x: x[1]["price"])[:3]
assert ranked[0][0] == "China Eastern", "cheapest full-service overall = China Eastern 8500"
assert len(ranked) == 2, "only 2 full-service airlines present"

# Case-insensitivity / substring match
assert hrb.is_full_service("Cathay Pacific Airways")
assert hrb.is_full_service("EVA AIR")
assert not hrb.is_full_service("Thai Vietjet Air")
assert not hrb.is_full_service("Scoot")

print("ALL ASSERTIONS PASSED")
