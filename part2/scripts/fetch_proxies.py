import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

PART2 = Path(__file__).resolve().parent.parent
OUTPUT = PART2 / "data" / "output"
RAW = OUTPUT / "raw_proxies"
COMPANIES = PART2.parent / "part1" / "data" / "input" / "companies_final.csv"

YEARS = range(2016, 2025)
FORMS = ["DEF 14A", "DEFC14A"]
PAUSE = 0.25

# Changed SEC IDs XOM and BLK use their old ID instead; AVGO adds its pre-2018 ID
EXTRA_CIKS = {
    "XOM": [34088],
    "BLK": [1364742],
    "AVGO": [1649338],
}
REPLACE_CIK = {"XOM", "BLK"}

load_dotenv(PART2 / ".env")
HEADERS = {"User-Agent": os.environ["SEC_USER_AGENT"]}


def get(url):
    """Download a URL from the SEC, retrying up to 5 times on any failure."""
    for attempt in range(5):
        time.sleep(PAUSE)
        try:
            r = requests.get(url, headers=HEADERS, timeout=120)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            print(f"    {type(e).__name__}, retrying", flush=True)
            time.sleep(10)
    raise RuntimeError(f"Gave up on {url}")


def get_json(url):
    """Download a URL and parse it as JSON."""
    return get(url).json()


def ticker_to_cik():
    """Map every ticker to its SEC company ID (CIK)."""
    data = get_json("https://www.sec.gov/files/company_tickers.json")
    return {row["ticker"]: row["cik_str"] for row in data.values()}


def all_filings(cik):
    """Return all filings under one SEC ID from 2015 onward."""
    sub = get_json(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
    pages = [sub["filings"]["recent"]]
    for f in sub["filings"]["files"]:
        if f["filingTo"] < f"{YEARS[0] - 1}-01-01":
            continue
        pages.append(get_json(f"https://data.sec.gov/submissions/{f['name']}"))
    filings = pd.concat([pd.DataFrame(p) for p in pages], ignore_index=True)
    filings["cik"] = cik
    return filings


def company_filings(ticker, ciks):
    """Combine a company's filings from all of its SEC IDs."""
    own = [] if ticker in REPLACE_CIK else [ciks[ticker.replace(".", "-")]]
    return pd.concat([all_filings(c) for c in own + EXTRA_CIKS.get(ticker, [])],
                     ignore_index=True)


def season_target(year, month):
    """Return the target filing date: mid-month of the company's usual filing month."""
    return pd.Timestamp(year, month, 15)


def pick_proxies(filings):
    """Choose one proxy per year, preferring the one filed closest to the usual month."""
    p = filings[filings.form.isin(FORMS)].copy()
    p["date"] = pd.to_datetime(p.filingDate)
    regular = p[p.form == "DEF 14A"]
    month = int((regular if len(regular) else p).date.dt.month.median())

    p["year"] = p.date.map(lambda d: min(
        (d.year - 1, d.year, d.year + 1),
        key=lambda y: abs(d - season_target(y, month))))
    p["days_off"] = (p.date - p.year.map(lambda y: season_target(y, month))).abs().dt.days
    p = p[p.year.isin(YEARS)]
    p["n_in_year"] = p.groupby("year").form.transform("size")

    p["contested"] = p.form == "DEFC14A"
    p["rank"] = p.days_off.where(~p.contested, -p["size"])
    return p.sort_values(["year", "contested", "rank", "size"], ascending=[True, True, True, False]).groupby("year").head(1)


def download(cik, row, path):
    """Save a filing's main document, skipping files already downloaded."""
    if path.exists():
        return
    acc = row.accessionNumber.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{row.primaryDocument}"
    content = get(url).content
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def main():
    """Download one proxy per company-year and write proxy_index.csv."""
    companies = pd.read_csv(COMPANIES)
    ciks = ticker_to_cik()
    index = []

    for _, co in companies.iterrows():
        print(co.ticker, flush=True)
        proxies = pick_proxies(company_filings(co.ticker, ciks)).set_index("year")

        for year in YEARS:
            row = {"ticker": co.ticker, "company_name": co.company_name,
                   "sector": co.sector, "year": year}
            if year not in proxies.index:
                index.append({**row, "status": "gap", "gap_reason": "no_proxy_filed_in_season"})
                continue
            p = proxies.loc[year]
            path = RAW / co.ticker / f"{year}.htm"
            download(p.cik, p, path)
            index.append({**row, "status": "ok", "form": p.form, "filing_date": p.filingDate,
                          "accession": p.accessionNumber, "n_proxies_in_season": p.n_in_year,
                          "size_bytes": path.stat().st_size,
                          "url": f"https://www.sec.gov/Archives/edgar/data/{p.cik}/"
                                 f"{p.accessionNumber.replace('-', '')}/{p.primaryDocument}"})

    index = pd.DataFrame(index)
    index.to_csv(OUTPUT / "proxy_index.csv", index=False)
    ok = (index.status == "ok").sum()
    print(f"\nProxies collected: {ok}/{len(index)} ({ok / len(index):.0%})")


main()
