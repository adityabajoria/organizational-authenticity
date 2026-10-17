import pandas as pd

from wayback import CDX_ENDPOINT, OUTPUT, YEARS, is_usable, polite_get, query_cdx

KEYWORDS = ("about|mission|values|purpose|philosophy|principles|"
            "who-we-are|company-info|our-company|credo|culture")

SEARCH_PREFIXES = {
    "GOOGL": ["google.com/about/", "about.google/"],
    "META": ["newsroom.fb.com/company-info", "about.fb.com/company-info"],
    "SBUX": ["starbucks.com/about-us"],
    "XOM": ["corporate.exxonmobil.com/", "exxonmobil.com/en/company"],
    "AAPL": ["investor.apple.com/", "apple.com/about"],
    "GS": ["goldmansachs.com/who-we-are/", "goldmansachs.com/our-firm/"],
    "SCHW": ["aboutschwab.com/"],
    "EOG": ["eogresources.com/"],
}

CANDIDATES = {
    "GOOGL": ["google.com/about/philosophy.html", "about.google/philosophy",
              "google.com/about/our-company", "google.com/about"],
    "META": ["newsroom.fb.com/company-info", "about.fb.com/company-info"],
    "SBUX": ["starbucks.com/about-us/company-information/mission-statement",
             "starbucks.com/about-us"],
    "XOM": ["corporate.exxonmobil.com/en/company/about-us",
            "corporate.exxonmobil.com/en/company/about-us/guiding-principles",
            "corporate.exxonmobil.com/en/company/who-we-are",
            "exxonmobil.com/en/company/about-us"],
    "AAPL": ["investor.apple.com/apple-values/default.aspx", "apple.com/about"],
    "GS": ["goldmansachs.com/who-we-are/business-standards/business-principles/index.html",
           "goldmansachs.com/our-firm/our-commitments/business-principles"],
    "SCHW": ["aboutschwab.com/about", "aboutschwab.com/who-we-are",
             "aboutschwab.com/our-purpose"],
    "EOG": ["eogresources.com/about", "eogresources.com/company"],
}


def search_prefix(prefix):
    """Search the archive for About-style URLs under a site prefix."""
    params = {
        "url": prefix,
        "matchType": "prefix",
        "from": str(YEARS[0]),
        "to": str(YEARS[-1]),
        "output": "json",
        "fl": "original,timestamp,statuscode",
        "collapse": "urlkey",
        "filter": [f"original:.*({KEYWORDS}).*", "statuscode:200"],
        "limit": "300",
    }
    r = polite_get(CDX_ENDPOINT, params=params)
    r.raise_for_status()
    rows = r.json() if r.text.strip() else []
    return [dict(zip(rows[0], row)) for row in rows[1:]] if rows else []


def main():
    """List candidate historical URLs and their yearly coverage for companies that moved their page."""
    found = []
    for ticker, prefixes in SEARCH_PREFIXES.items():
        for prefix in prefixes:
            print(f"{ticker:6s} searching {prefix}", flush=True)
            for c in search_prefix(prefix):
                found.append({"ticker": ticker, "prefix": prefix,
                              "candidate_url": c["original"],
                              "first_seen": c["timestamp"][:8]})
    pd.DataFrame(found).to_csv(OUTPUT / "url_candidates.csv", index=False)

    coverage = []
    for ticker, urls in CANDIDATES.items():
        for url in urls:
            captures = query_cdx(url)
            row = {"ticker": ticker, "url": url}
            for year in YEARS:
                row[year] = sum(1 for c in captures
                                if c["timestamp"].startswith(str(year)) and is_usable(c))
            coverage.append(row)
    coverage = pd.DataFrame(coverage)
    coverage.to_csv(OUTPUT / "url_candidate_coverage.csv", index=False)
    print(coverage.to_string(index=False))


main()
