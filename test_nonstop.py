"""Synthetic test: nonstop detection in iter_fares + direct-only filter.
Run: GMAIL_USER=x GMAIL_APP_PASSWORD=x GOOGLE_SERVICE_ACCOUNT_JSON={} GOOGLE_SHEET_ID=x python -X utf8 test_nonstop.py
No network. Validates parser + bkk_can_monitor reduction.
"""
import flight_core as core
import bkk_can_monitor as can


def fare(dep, arr, name, dur, stops_line, price):
    # Google Flights line layout: dep / - / arr / airline / dur / stops / price
    return f"{dep}\n-\n{arr}\n{name}\n{dur}\n{stops_line}\nTHB {price}\n"


body = (
    fare("7:40 AM", "1:30 PM", "China Southern", "5 hr 50 min", "Nonstop", "9,800")
    + fare("9:00 AM", "8:00 PM", "Cathay Pacific", "13 hr 0 min", "1 stop", "7,200")
    + fare("10:15 AM", "4:05 PM", "Thai AirAsia", "5 hr 50 min", "Nonstop", "8,500")
    + fare("6:00 PM", "11:50 PM", "China Southern", "5 hr 50 min", "Nonstop", "10,400")
)

fares = list(core.iter_fares(body, "http://x"))
print("total fares parsed:", len(fares))
for name, f in fares:
    print(f"  {name:18} THB{f['price']:>6,}  stops={f['stops']}")

direct = can.cheapest_direct_per_airline(body, "http://x")
print("direct-only cheapest per airline:")
for name, f in sorted(direct.items(), key=lambda x: x[1]["price"]):
    print(f"  {name:18} THB{f['price']:>6,}  stops={f['stops']}")

# Assertions
assert len(fares) == 4, "should parse 4 fares"
stops_map = {n: f["stops"] for n, f in fares}
assert stops_map["Cathay Pacific"] == 1
assert stops_map["Thai AirAsia"] == 0
assert "Cathay Pacific" not in direct, "1-stop must be excluded"
assert direct["China Southern"]["price"] == 9800, "cheapest nonstop CZ = 9800"
assert direct["Thai AirAsia"]["price"] == 8500
ranked = sorted(direct.items(), key=lambda x: x[1]["price"])[:3]
assert ranked[0][0] == "Thai AirAsia", "cheapest direct overall = AirAsia 8500"

# Undetected-stops case kept (URL trusted)
body2 = "7:40 AM\n-\n1:30 PM\nJAL\n5 hr 50 min\nThai\nTHB 12,000\n"
d2 = can.cheapest_direct_per_airline(body2, "http://x")
assert d2.get("JAL", {}).get("price") == 12000, "undetected stops must be kept"

print("ALL ASSERTIONS PASSED")
