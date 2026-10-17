import json
import re
import shutil
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd

from wayback import DATA, YEARS, is_usable, polite_get, query_cdx, ts_to_datetime

RAW = DATA / "raw_html"
MAX_REDIRECT_HOPS = 5
REDIRECTS_TO_TRY = 2
FETCH_ATTEMPTS = 3
WAYBACK_URL = re.compile(r"web\.archive\.org/web/(\d{14})[a-z_]*/(.+)$")

INDEX_COLUMNS = ["ticker", "company_name", "sector", "year", "status", "gap_reason",
                 "about_url", "snapshot_date", "days_from_july1",
                 "n_candidates_in_year", "redirected_from", "wayback_url"]


def url_for_year(timeline, ticker, year, default):
    rows = timeline[timeline.ticker == ticker]
    if rows.empty:
        return default
    match = rows[(rows.valid_from <= year) & (rows.valid_to >= year)]
    if match.empty:
        return None
    return match.iloc[0].url


def captures_in_year(captures, year):
    return [c for c in captures if c["timestamp"].startswith(str(year))]


def distance_to_midyear(capture, year):
    return abs(ts_to_datetime(capture["timestamp"]) - datetime(year, 7, 1))


def usable_by_distance(captures, year):
    candidates = [c for c in captures_in_year(captures, year) if is_usable(c)]
    return sorted(candidates, key=lambda c: distance_to_midyear(c, year))


def pick_closest_to_midyear(captures, year):
    candidates = usable_by_distance(captures, year)
    return (candidates[0] if candidates else None), len(candidates)


def site_domain(url):
    host = urlparse(url if "://" in url else "http://" + url).hostname or ""
    return ".".join(host.split(".")[-2:])


def resolve_redirect(capture, about_url, year):
    r = polite_get(f"https://web.archive.org/web/{capture['timestamp']}/{capture['original']}")
    m = WAYBACK_URL.search(r.url)
    if r.status_code != 200 or not m or len(r.history) > MAX_REDIRECT_HOPS:
        return None
    ts, dest = m.groups()
    if not ts.startswith(str(year)) or site_domain(dest) != site_domain(about_url):
        return None
    return {"timestamp": ts, "original": dest, "digest": "",
            "redirected_from": capture["original"]}


def download_raw(capture):
    r = polite_get(f"https://web.archive.org/web/{capture['timestamp']}id_/{capture['original']}")
    return r.content if r.status_code == 200 else None


def gap_reason(captures, year):
    in_year = captures_in_year(captures, year)
    if not in_year:
        return "no_captures_in_year"
    if any(c["statuscode"].startswith("3") for c in in_year):
        return "redirects_left_domain_or_year"
    return "only_error_captures"


def snapshot_meta(cap, year, n_candidates):
    taken = ts_to_datetime(cap["timestamp"])
    return {
        "status": "ok",
        "timestamp": cap["timestamp"],
        "snapshot_date": taken.date().isoformat(),
        "days_from_july1": abs((taken - datetime(year, 7, 1)).days),
        "original": cap["original"],
        "digest": cap.get("digest", ""),
        "n_candidates_in_year": n_candidates,
        "redirected_from": cap.get("redirected_from", ""),
        "wayback_url": f"https://web.archive.org/web/{cap['timestamp']}/{cap['original']}",
    }


def main():
    companies = pd.read_csv(DATA / "companies_final.csv")
    timeline = pd.read_csv(DATA / "url_timeline.csv")
    index = []

    for i, co in companies.iterrows():
        print(f"[{i + 1:2d}/{len(companies)}] {co.ticker}", flush=True)
        out_dir = RAW / co.ticker
        out_dir.mkdir(parents=True, exist_ok=True)
        saved_by_digest = {}

        for year in YEARS:
            html_path = out_dir / f"{year}.html"
            meta_path = out_dir / f"{year}.json"
            url = url_for_year(timeline, co.ticker, year, co.about_url)
            row = {"ticker": co.ticker, "company_name": co.company_name,
                   "sector": co.sector, "year": year,
                   "about_url": url or ""}

            if url is None:
                print(f"    {year}: GAP (no archived URL for this year)", flush=True)
                index.append({**row, "status": "gap", "gap_reason": "no_archived_url_for_year"})
                continue

            if html_path.exists() and meta_path.exists():
                meta = json.loads(meta_path.read_text())
                if meta.get("digest"):
                    saved_by_digest.setdefault(meta["digest"], html_path)
                index.append({**row, **meta})
                continue

            captures = query_cdx(url)
            cap, n_candidates = pick_closest_to_midyear(captures, year)
            if cap is None:
                redirects = sorted(
                    (c for c in captures_in_year(captures, year)
                     if c["statuscode"].startswith("3")),
                    key=lambda c: distance_to_midyear(c, year))
                for red in redirects[:REDIRECTS_TO_TRY]:
                    cap = resolve_redirect(red, url, year)
                    if cap:
                        break

            if cap is None:
                reason = gap_reason(captures, year)
                print(f"    {year}: GAP ({reason})", flush=True)
                index.append({**row, "status": "gap", "gap_reason": reason})
                continue

            digest = cap.get("digest", "")
            if digest in saved_by_digest:
                shutil.copy(saved_by_digest[digest], html_path)
            else:
                content = download_raw(cap)
                if content is None and "redirected_from" not in cap:
                    for alt in usable_by_distance(captures, year)[1:FETCH_ATTEMPTS]:
                        content = download_raw(alt)
                        if content is not None:
                            cap, digest = alt, alt.get("digest", "")
                            break
                if content is None:
                    print(f"    {year}: fetch failed", flush=True)
                    index.append({**row, "status": "gap", "gap_reason": "fetch_failed",
                                  "timestamp": cap["timestamp"]})
                    continue
                html_path.write_bytes(content)
                if digest:
                    saved_by_digest[digest] = html_path

            meta = snapshot_meta(cap, year, n_candidates)
            meta_path.write_text(json.dumps(meta, indent=2))
            index.append({**row, **meta})
            print(f"    {year}: ok {meta['snapshot_date']}", flush=True)

    index = pd.DataFrame(index).reindex(columns=INDEX_COLUMNS)
    for col in ["days_from_july1", "n_candidates_in_year"]:
        index[col] = index[col].astype("Int64")
    index.to_csv(DATA / "snapshot_index.csv", index=False)

    ok = (index.status == "ok").sum()
    print(f"\nSnapshots collected: {ok}/{len(index)} ({ok / len(index):.0%})")
    print(index[index.status == "gap"].groupby("gap_reason").size().to_string())


main()
