"""Integration test for v2 native functions."""

import csv
import io
import math
import hashlib
import time

from _leadswarm_native import (
    serialize_prospects_csv,
    serialize_prospects_json,
    fast_cache_key,
    haversine_distance,
    batch_haversine,
    extract_html_metadata,
    normalize_domain,
    extract_emails,
)


def py_haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def py_csv_export(prospects):
    output = io.StringIO()
    fieldnames = ["name", "website", "phone", "address", "emails",
        "rating", "review_count", "fit_score", "opportunity_score",
        "priority_score", "opportunity_notes", "found_in_ads",
        "found_in_maps", "found_in_organic", "cms",
        "has_google_analytics", "has_booking_system"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for p in prospects:
        signals = p.get("signals", {})
        writer.writerow({
            "name": p.get("name", ""),
            "website": p.get("website", ""),
            "phone": p.get("phone", ""),
            "address": p.get("address", ""),
            "emails": "; ".join(p.get("emails", [])),
            "rating": p.get("rating", ""),
            "review_count": p.get("review_count", ""),
            "fit_score": p.get("fit_score", 0),
            "opportunity_score": p.get("opportunity_score", 0),
            "priority_score": round(p.get("priority_score", 0), 1),
            "opportunity_notes": p.get("opportunity_notes", ""),
            "found_in_ads": "Yes" if p.get("found_in_ads") else "No",
            "found_in_maps": "Yes" if p.get("found_in_maps") else "No",
            "found_in_organic": "Yes" if p.get("found_in_organic") else "No",
            "cms": signals.get("cms", ""),
            "has_google_analytics": "Yes" if signals.get("has_google_analytics") else "No",
            "has_booking_system": "Yes" if signals.get("has_booking") else "No",
        })
    return output.getvalue()


passed = 0
failed = 0

def test(name, condition):
    global passed, failed
    if condition:
        print(f"  PASS  {name}")
        passed += 1
    else:
        print(f"  FAIL  {name}")
        failed += 1


print("=" * 60)
print("LeadSwarm Native v2 Integration Test")
print("=" * 60)

# --- Export CSV ---
print("\n[serialize_prospects_csv]")
prospects = [
    {
        "name": "Test Plumber",
        "website": "https://testplumber.com",
        "phone": "0412345678",
        "address": "123 Main St",
        "emails": ["info@test.com"],
        "rating": 4.5,
        "review_count": 42,
        "fit_score": 75,
        "opportunity_score": 60,
        "priority_score": 67.5,
        "opportunity_notes": "No analytics",
        "found_in_ads": True,
        "found_in_maps": True,
        "found_in_organic": False,
        "signals": {
            "cms": "WordPress",
            "has_google_analytics": True,
            "has_booking_system": False,
        },
    }
]
csv_out = serialize_prospects_csv(prospects)
test("CSV contains header", "name,website,phone" in csv_out)
test("CSV contains data", "Test Plumber" in csv_out)
test("CSV bool Yes/No", "Yes" in csv_out)
test("CSV rating", "4.5" in csv_out)

# --- Export JSON ---
print("\n[serialize_prospects_json]")
prospects[0]["domain"] = "testplumber.com"
prospects[0]["category"] = "Plumbing"
json_out = serialize_prospects_json(prospects, True)
test("JSON contains name", '"Test Plumber"' in json_out)
test("JSON has serp_presence", '"serp_presence"' in json_out)
test("JSON has scores", '"scores"' in json_out)
test("JSON pretty has newlines", "\n" in json_out)

compact = serialize_prospects_json(prospects, False)
test("JSON compact no newlines", "\n" not in compact)

# --- Cache key ---
print("\n[fast_cache_key]")
key1 = fast_cache_key("plumber", "Brisbane")
key2 = fast_cache_key("Plumber", "brisbane")
key3 = fast_cache_key("electrician", "Brisbane")
test("Cache key is hex string", all(c in "0123456789abcdef" for c in key1))
test("Cache key 16 chars", len(key1) == 16)
test("Case insensitive", key1 == key2)
test("Different queries differ", key1 != key3)

# --- Haversine ---
print("\n[haversine_distance]")
dist = haversine_distance(-27.4698, 153.0251, -27.4818, 153.0205)
test("Distance reasonable (0.5-3km)", 0.5 < dist < 3.0)

dist_zero = haversine_distance(-27.4698, 153.0251, -27.4698, 153.0251)
test("Same point = 0", dist_zero < 0.001)

py_dist = py_haversine(-27.4698, 153.0251, -27.4818, 153.0205)
test(f"Matches Python ({dist:.6f} vs {py_dist:.6f})", abs(dist - py_dist) < 0.001)

# --- Batch haversine ---
print("\n[batch_haversine]")
points = [(-27.4818, 153.0205), (-27.4568, 153.0358), (-27.4833, 153.0089)]
dists = batch_haversine(-27.4698, 153.0251, points)
test("Returns correct count", len(dists) == 3)
test("All positive", all(d >= 0 for d in dists))
test("First matches single call", abs(dists[0] - dist) < 0.001)

# --- HTML metadata ---
print("\n[extract_html_metadata]")
html = """
<html><head>
<title>Best Plumber Brisbane | 24/7 Emergency</title>
<meta name="description" content="Professional plumbing services in Brisbane.">
</head><body>
<a href="https://facebook.com/testplumber">Facebook</a>
<a href="https://instagram.com/testplumber">Instagram</a>
<a href="https://example.com">Not social</a>
<a href="https://linkedin.com/company/test">LinkedIn</a>
</body></html>
"""
meta = extract_html_metadata(html)
test("Title extracted", meta["title"] == "Best Plumber Brisbane | 24/7 Emergency")
test("Meta description", meta["meta_description"] == "Professional plumbing services in Brisbane.")
test("Social links count = 3", len(meta["social_links"]) == 3)
test("Facebook in links", any("facebook.com" in l for l in meta["social_links"]))
test("Instagram in links", any("instagram.com" in l for l in meta["social_links"]))
test("LinkedIn in links", any("linkedin.com" in l for l in meta["social_links"]))

empty_meta = extract_html_metadata("")
test("Empty HTML title is None", empty_meta["title"] is None)
test("Empty HTML social_links is []", empty_meta["social_links"] == [])

# --- V1 sanity check ---
print("\n[v1 sanity check]")
test("normalize_domain works", normalize_domain("https://www.example.com/page") == "example.com")
test("extract_emails works", "info@example.com" in extract_emails("Email: info@example.com"))

# --- Benchmark ---
print(f"\n{'=' * 60}")
print("Quick Benchmark")
print("=" * 60)

big_prospects = prospects * 200
start = time.perf_counter()
for _ in range(10):
    serialize_prospects_csv(big_prospects)
rust_csv = time.perf_counter() - start

start = time.perf_counter()
for _ in range(10):
    py_csv_export(big_prospects)
py_csv = time.perf_counter() - start
print(f"CSV export (200 prospects x10): Rust {rust_csv*1000:.1f}ms  Python {py_csv*1000:.1f}ms  Speedup: {py_csv/rust_csv:.1f}x")

start = time.perf_counter()
for i in range(10000):
    fast_cache_key(f"plumber_{i}", "Brisbane")
rust_hash = time.perf_counter() - start

start = time.perf_counter()
for i in range(10000):
    hashlib.md5(f"plumber_{i}|brisbane".encode()).hexdigest()
py_hash = time.perf_counter() - start
print(f"Cache key (10k hashes):         Rust {rust_hash*1000:.1f}ms  Python {py_hash*1000:.1f}ms  Speedup: {py_hash/rust_hash:.1f}x")

pts = [(-27.4818 + i*0.001, 153.0205 + i*0.001) for i in range(100)]
start = time.perf_counter()
for _ in range(1000):
    batch_haversine(-27.4698, 153.0251, pts)
rust_geo = time.perf_counter() - start

start = time.perf_counter()
for _ in range(1000):
    for lat, lng in pts:
        py_haversine(-27.4698, 153.0251, lat, lng)
py_geo = time.perf_counter() - start
print(f"Haversine (100 pts x1000):      Rust {rust_geo*1000:.1f}ms  Python {py_geo*1000:.1f}ms  Speedup: {py_geo/rust_geo:.1f}x")

big_html = html * 50
start = time.perf_counter()
for _ in range(100):
    extract_html_metadata(big_html)
rust_meta = time.perf_counter() - start

from bs4 import BeautifulSoup
start = time.perf_counter()
for _ in range(100):
    soup = BeautifulSoup(big_html, "lxml")
    soup.find("title")
    soup.find("meta", attrs={"name": "description"})
    for link in soup.find_all("a", href=True):
        pass
py_meta = time.perf_counter() - start
print(f"HTML metadata (big x100):       Rust {rust_meta*1000:.1f}ms  Python {py_meta*1000:.1f}ms  Speedup: {py_meta/rust_meta:.1f}x")

print(f"\n{'=' * 60}")
print(f"Results: {passed} passed, {failed} failed")
print(f"{'=' * 60}")
