import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

import requests

PART1 = Path(__file__).resolve().parent.parent
DATA = PART1 / "data"
INPUT = DATA / "input"
OUTPUT = DATA / "output"
FINAL = DATA / "final"
CDX_CACHE = OUTPUT / "cdx_cache"

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
YEARS = list(range(2016, 2025))
HEADERS = {"User-Agent": "Academic research (Wharton RA task)"}

PACE_SECONDS = 5
RATE_LIMIT_WAIT = 300
SERVER_ERROR_WAIT = 60
MAX_ATTEMPTS = 12

_last_request = 0.0


def polite_get(url, params=None, timeout=120):
    global _last_request
    for attempt in range(1, MAX_ATTEMPTS + 1):
        wait = PACE_SECONDS - (time.time() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.time()

        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        except requests.RequestException as e:
            print(f"    network error ({type(e).__name__}), retry {attempt}", flush=True)
            time.sleep(SERVER_ERROR_WAIT)
            continue

        if r.status_code == 429:
            print(f"    rate limited, retry {attempt}", flush=True)
            time.sleep(RATE_LIMIT_WAIT)
        elif r.status_code >= 500:
            print(f"    HTTP {r.status_code}, retry {attempt}", flush=True)
            time.sleep(SERVER_ERROR_WAIT)
        else:
            return r

    raise RuntimeError(f"Gave up on {url} after {MAX_ATTEMPTS} attempts")


def normalize_url(url):
    return url.strip().rstrip("/")


def query_cdx(url):
    url = normalize_url(url)
    path = CDX_CACHE / (hashlib.md5(url.encode()).hexdigest() + ".json")
    if path.exists():
        return json.loads(path.read_text())

    params = {
        "url": url,
        "from": str(YEARS[0]),
        "to": str(YEARS[-1]),
        "output": "json",
        "fl": "timestamp,original,statuscode,mimetype,digest",
        "collapse": "timestamp:8",
    }
    r = polite_get(CDX_ENDPOINT, params=params)
    r.raise_for_status()

    rows = r.json() if r.text.strip() else []
    captures = [dict(zip(rows[0], row)) for row in rows[1:]] if rows else []

    CDX_CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(captures))
    return captures


def is_usable(capture):
    if capture["statuscode"] == "200" and "html" in capture["mimetype"]:
        return True
    return capture["mimetype"] == "warc/revisit"


def ts_to_datetime(ts):
    return datetime.strptime(ts[:14], "%Y%m%d%H%M%S")
