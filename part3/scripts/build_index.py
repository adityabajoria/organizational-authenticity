from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
ABOUT = ROOT / "part1" / "data" / "final" / "final_dataset.csv"
PROXY = ROOT / "part2" / "data" / "final" / "final_dataset.csv"
FINAL = ROOT / "part3" / "data" / "final"

THEMES = ["integrity", "innovation", "customer", "collaboration", "diversity_inclusion",
          "performance", "adaptability", "community", "safety", "sustainability"]


def sector_percentiles(proxies):
    """Rank each proxy's emphasis on every theme against companies in the same sector and year (0-1)."""
    return proxies.set_index(["ticker", "year"]).groupby(["year", "sector"])[THEMES].rank(pct=True)


def stated_themes(about):
    """Return the themes each usable About page states, as a list per company-year."""
    usable = about[(about.status == "ok") & (about.theme_categories != "MISSING")]
    return usable.set_index(["ticker", "year"]).theme_categories.str.split(";")


def authenticity(pct, stated):
    """Return how much more the proxy emphasises the stated themes than its own average theme (-100 to 100)."""
    return round(100 * (pct[stated].mean() - pct.mean()), 1)


def main():
    """Score every company-year with both an About page and a proxy, and write final_dataset.csv."""
    about = pd.read_csv(ABOUT, keep_default_na=False)
    pct = sector_percentiles(pd.read_csv(PROXY))

    rows = [{"ticker": ticker, "year": year, "theme": ";".join(stated), "number_of_themes": len(stated),
             "authenticity_index": authenticity(pct.loc[(ticker, year)], stated)}
            for (ticker, year), stated in stated_themes(about).items()]

    names = about[["ticker", "company_name", "sector"]].drop_duplicates()
    df = names.merge(pd.DataFrame(rows), on="ticker").sort_values(["ticker", "year"])
    df["authenticity_percentile"] = (df.authenticity_index.rank() / (len(df) + 1)).round(3)
    FINAL.mkdir(parents=True, exist_ok=True)
    df.to_csv(FINAL / "final_dataset.csv", index=False)
    print(f"Saved {len(df)} company-years for {df.ticker.nunique()} companies to data/final/final_dataset.csv")


main()
