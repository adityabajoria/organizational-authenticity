from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
ABOUT = ROOT / "part1" / "data" / "final" / "final_dataset.csv"
PROXY = ROOT / "part2" / "data" / "final" / "final_dataset.csv"
FINAL = ROOT / "part4" / "data" / "final"

THEMES = ["integrity", "innovation", "customer", "collaboration", "diversity_inclusion",
          "performance", "adaptability", "community", "safety", "sustainability"]
PROXY_THRESHOLD = 1.0
EARLY, LATE = (2016, 2018), (2022, 2024)


def matched_panel():
    """Return company-years with both documents, marking which themes each discusses."""
    about = pd.read_csv(ABOUT, keep_default_na=False)
    about = about[about.status == "ok"]
    proxy = pd.read_csv(PROXY)
    panel = about[["ticker", "year", "theme_categories"]].merge(proxy, on=["ticker", "year"])
    for theme in THEMES:
        panel[f"{theme}_about"] = panel.theme_categories.str.split(";").map(lambda s: theme in s)
        panel[f"{theme}_proxy"] = panel[theme] >= PROXY_THRESHOLD
    return panel


def by_year(panel):
    """Return, for every theme and year, the % of companies discussing it in each document type."""
    rows = []
    for year, group in panel.groupby("year"):
        for theme in THEMES:
            rows.append({"theme": theme, "year": year, "companies": len(group),
                         "about_page_pct": round(100 * group[f"{theme}_about"].mean(), 1),
                         "proxy_pct": round(100 * group[f"{theme}_proxy"].mean(), 1)})
    return pd.DataFrame(rows)


def summary(yearly):
    """Return each theme's early and late levels and the year proxies first overtook About pages."""
    rows = []
    for theme, g in yearly.groupby("theme", sort=False):
        early, late = g[g.year.between(*EARLY)].mean(numeric_only=True), g[g.year.between(*LATE)].mean(numeric_only=True)
        ahead = g[g.proxy_pct > g.about_page_pct].year
        rows.append({"theme": theme,
                     "about_page_2016_18": round(early.about_page_pct), "about_page_2022_24": round(late.about_page_pct),
                     "proxy_2016_18": round(early.proxy_pct), "proxy_2022_24": round(late.proxy_pct),
                     "proxy_ahead_from": int(ahead.min()) if len(ahead) else "never"})
    return pd.DataFrame(rows)


def main():
    """Build the yearly theme comparison and summary; write both to data/final."""
    yearly = by_year(matched_panel())
    FINAL.mkdir(parents=True, exist_ok=True)
    yearly.to_csv(FINAL / "theme_by_year.csv", index=False)
    table = summary(yearly)
    table.to_csv(FINAL / "theme_summary.csv", index=False)
    print(table.to_string(index=False))


main()
