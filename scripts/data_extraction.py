import os
import json
import time
import argparse
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CYCLONE_CATALOG = [
    {"Year": "2025", "Cyclonelist": ["SHAKHTI", "MONTHA", "SENYAR", "DITWAH"]},
    {"Year": "2024", "Cyclonelist": ["REMAL", "ASNA", "DANA", "FENGAL"]},
    {"Year": "2023", "Cyclonelist": ["MOCHA", "BIPARJOY", "TEJ", "HAMOON", "MIDHILI", "MICHAUNG"]},
    {"Year": "2022", "Cyclonelist": ["ASANI", "SITRANG", "MANDOUS"]},
    {"Year": "2021", "Cyclonelist": ["GULAB", "JAWAD", "SHAHEEN", "TAUKTAE", "YAAS"]},
    {"Year": "2020", "Cyclonelist": ["AMPHAN", "BUREVI", "GATI", "NISARGA", "NIVAR"]},
    {"Year": "2019", "Cyclonelist": ["BULBUL", "FANI", "HIKKA", "KYAAR", "MAHA", "PAWAN", "VAYU"]},
    {"Year": "2018", "Cyclonelist": ["DAYE", "GAJA", "LUBAN", "MEKUNU", "PHETHAI", "TITLI"]},
    {"Year": "2017", "Cyclonelist": ["MAARUTHA", "MORA", "OCKHI"]},
    {"Year": "2016", "Cyclonelist": ["KYANT", "NADA", "ROANU", "VARDAH"]},
    {"Year": "2015", "Cyclonelist": ["ASHOBAA", "CHAPALA", "MEGH"]},
    {"Year": "2014", "Cyclonelist": ["HUDHUD", "NANAUK", "NILOFAR"]},
    {"Year": "2013", "Cyclonelist": ["HELEN", "LEHAR", "MADI", "PHAILIN"]},
]

TRACK_URL = "https://mosdac.gov.in/app_php/getprevcyclonetrack_new.php"

DEFAULT_COOKIE = (
    "Three; _pk_id.1.e0e7=43eb613a3be8378d.1784274862.; "
    "_pk_ref.1.e0e7=%5B%22%22%2C%22%22%2C1791697760%2C%22https%3A%2F%2Fwww.mosdac.gov.in%2F%22%5D; "
    "_pk_ses.1.e0e7=1; PHPSESSID=c55497a1189a1416fabb479916698262; Three"
)

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.6",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
    "Cookie": os.environ.get("MOSDAC_COOKIE", DEFAULT_COOKIE),
    "Origin": "https://mosdac.gov.in",
    "Referer": "https://mosdac.gov.in/scorpio/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-GPC": "1",
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"),
    "sec-ch-ua": '"Chromium";v="154", "Brave";v="154", "Not A(Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
}
# Host and Content-Length are set automatically by requests.

OUT_DIR = "data"
RAW_DIR = os.path.join(OUT_DIR, "raw")
OUT_FILE = os.path.join(OUT_DIR, "mosdac_all_cyclones.geojson")

session = requests.Session()
session.verify = False  # ignore the SSL certificate error


def point_to_feature(p):
    """Turn a plain record with lat/lon fields into a GeoJSON Point feature."""
    keys = {k.lower(): k for k in p}
    lat_k = next((keys[k] for k in ("lat", "latitude", "y") if k in keys), None)
    lon_k = next((keys[k] for k in ("lon", "lng", "long", "longitude", "x") if k in keys), None)
    if not lat_k or not lon_k:
        return None
    try:
        lat, lon = float(p[lat_k]), float(p[lon_k])
    except (TypeError, ValueError):
        return None
    return {"type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": dict(p)}


def extract_features(data):
    """Handle a GeoJSON FeatureCollection, a list of features, or a list of points."""
    if isinstance(data, dict):
        if isinstance(data.get("features"), list):
            return data["features"]
        for key in ("data", "track", "result", "points"):
            if key in data:
                return extract_features(data[key])
        return []
    if isinstance(data, list):
        if data and isinstance(data[0], dict) and data[0].get("type") == "Feature":
            return data
        feats = [point_to_feature(p) for p in data if isinstance(p, dict)]
        return [f for f in feats if f]
    return []


def fetch_track(cyclone_name, retries=2):
    # Compact JSON, byte-for-byte identical to the browser body:
    # {"cyclone_name":"SHAKHTI"}
    body = json.dumps({"cyclone_name": cyclone_name}, separators=(",", ":"))

    last_error = "unknown error"
    for attempt in range(retries + 1):
        try:
            res = session.post(TRACK_URL, data=body, headers=HEADERS, timeout=30)
        except requests.RequestException as e:
            last_error = f"{type(e).__name__}: {e}"
            time.sleep(2)
            continue

        snippet = res.text[:200].replace("\n", " ")
        if res.status_code != 200:
            last_error = f"HTTP {res.status_code}: {snippet!r}"
            if res.status_code >= 500:
                time.sleep(2)
                continue
            return None, last_error, None

        try:
            data = json.loads(res.text.lstrip("\ufeff").strip())
        except json.JSONDecodeError:
            return None, f"non-JSON response: {snippet!r}", None

        features = extract_features(data)
        if not features:
            return None, f"JSON returned but no track points: {snippet!r}", data
        return features, None, data

    return None, last_error, None


def main():
    ap = argparse.ArgumentParser(description="MOSDAC SCORPIO cyclone track extractor")
    ap.add_argument("--test", action="store_true", help="fetch only SHAKHTI and print the response")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    args = ap.parse_args()

    os.makedirs(RAW_DIR, exist_ok=True)

    if args.test:
        features, err, data = fetch_track("SHAKHTI")
        print("Error:" if err else "OK:", err or f"{len(features)} points")
        if data is not None:
            print(json.dumps(data, indent=2)[:1500])
        return

    master_features, failures = [], []
    total = sum(len(x["Cyclonelist"]) for x in CYCLONE_CATALOG)
    success_count, idx = 0, 0

    print("=== MOSDAC SCORPIO Cyclone Extraction Pipeline ===")
    print(f"Targeting {total} cyclones across 2013-2025...\n")

    for entry in CYCLONE_CATALOG:
        yr = entry["Year"]
        for cname in entry["Cyclonelist"]:
            idx += 1
            print(f"[{idx}/{total}] Fetching {cname} ({yr})...", end=" ", flush=True)

            features, err, data = fetch_track(cname)

            if data is not None:  # keep raw responses for inspection/reprocessing
                with open(os.path.join(RAW_DIR, f"{yr}_{cname}.json"), "w", encoding="utf-8") as f:
                    json.dump(data, f)

            if features:
                success_count += 1
                print(f"SUCCESS ({len(features)} points)")
                for seq, feat in enumerate(features):
                    props = feat.get("properties") or {}
                    props["cyclone_name"] = cname.upper()
                    props["year"] = int(yr)
                    props["point_seq"] = seq + 1
                    feat["properties"] = props
                    master_features.append(feat)
            else:
                print(f"FAILED: {err}")
                failures.append({"cyclone": cname, "year": yr, "reason": err})

            time.sleep(args.delay)

    master_geojson = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": master_features,
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(master_geojson, f, indent=2)

    if failures:
        with open(os.path.join(OUT_DIR, "failures.json"), "w", encoding="utf-8") as f:
            json.dump(failures, f, indent=2)

    print("\n" + "=" * 50)
    print("PIPELINE EXECUTION COMPLETE")
    print(f"Successfully Extracted: {success_count} / {total} cyclones")
    print(f"Total Waypoints Saved : {len(master_features)}")
    print(f"Saved to              : {OUT_FILE}")
    if failures:
        print(f"Failures logged to    : {os.path.join(OUT_DIR, 'failures.json')}")
    print("=" * 50)


if __name__ == "__main__":
    main()