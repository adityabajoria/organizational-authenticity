from math import erf, sqrt
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
ABOUT = ROOT / "part1" / "data" / "final" / "final_dataset.csv"
PROXY = ROOT / "part2" / "data" / "final" / "final_dataset.csv"
FINAL = ROOT / "part4" / "data" / "final"
VISUALIZATIONS = ROOT / "part4" / "visualizations"

THEMES = ["integrity", "innovation", "customer", "collaboration", "diversity_inclusion",
          "performance", "adaptability", "community", "safety", "sustainability"]
THRESHOLDS = [0.5, 1.0, 2.0]
MAIN_THRESHOLD = 1.0


def gaps(threshold):
    """Return, for every company-year and theme, the proxy minus About page indicator (-1, 0 or 1)."""
    about = pd.read_csv(ABOUT, keep_default_na=False)
    about = about[about.status == "ok"]
    panel = about[["ticker", "year", "sector", "theme_categories"]].merge(
        pd.read_csv(PROXY).drop(columns=["company_name", "sector"]), on=["ticker", "year"])
    for theme in THEMES:
        on_page = panel.theme_categories.str.split(";").map(lambda s: theme in s)
        panel[f"{theme}_gap"] = (panel[theme] >= threshold).astype(int) - on_page.astype(int)
    return panel


def within_company_trend(df, column):
    """Return the yearly change in a gap within the same companies, with a company-clustered standard error."""
    y = df[column] - df.groupby("ticker")[column].transform("mean")
    x = df.year - df.groupby("ticker").year.transform("mean")
    slope = (x * y).sum() / (x * x).sum()
    scores = (x * (y - slope * x)).groupby(df.ticker).sum()
    n = len(scores)
    se = sqrt(n / (n - 1) * (scores ** 2).sum()) / (x * x).sum()
    p = 2 * (1 - 0.5 * (1 + erf(abs(slope / se) / sqrt(2))))
    return 100 * slope, 100 * se, p


def direction(slope, p):
    """Describe which document type is gaining ground on a theme."""
    if p >= 0.05:
        return "no clear trend"
    return "proxies gaining" if slope > 0 else "About pages gaining"


def trend_table():
    """Return each theme's gap trend at the main threshold, and the same trend at the other thresholds."""
    results = {t: gaps(t) for t in THRESHOLDS}
    main = results[MAIN_THRESHOLD]
    rows = []
    for theme in THEMES:
        col = f"{theme}_gap"
        slope, se, p = within_company_trend(main, col)
        others = {t: within_company_trend(results[t], col) for t in THRESHOLDS if t != MAIN_THRESHOLD}
        robust = all(np.sign(o[0]) == np.sign(slope) and o[2] < 0.05 for o in others.values()) and p < 0.05
        rows.append({"theme": theme,
                     "gap_2016_18": round(100 * main[main.year <= 2018][col].mean()),
                     "gap_2022_24": round(100 * main[main.year >= 2022][col].mean()),
                     "gap_change_per_year": round(slope, 1), "std_error": round(se, 1), "p_value": round(p, 3),
                     "direction": direction(slope, p),
                     **{f"change_at_{t}pct_threshold": round(o[0], 1) for t, o in others.items()},
                     "robust_to_threshold": "yes" if robust else "no"})
    return pd.DataFrame(rows).sort_values("gap_change_per_year", ascending=False)


def sector_table():
    """Return each theme's within-company gap trend separately for every sector."""
    panel = gaps(MAIN_THRESHOLD)
    rows = {sector: {theme: round(within_company_trend(g, f"{theme}_gap")[0], 1) for theme in THEMES}
            for sector, g in panel.groupby("sector")}
    return pd.DataFrame(rows).T.rename_axis("sector").reset_index()


def plot(table):
    """Save a chart of each theme's yearly gap change with a 95% confidence interval."""
    t = table.sort_values("gap_change_per_year")
    colors = ["#7b4bc4" if d == "proxies gaining" else "#e8590c" if d == "About pages gaining" else "#9e9e9e"
              for d in t.direction]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    names = [n.replace("diversity_inclusion", "diversity and inclusion").capitalize() for n in t.theme]
    ax.barh(names, t.gap_change_per_year, xerr=1.96 * t.std_error, color=colors, capsize=3)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Change in gap per year (percentage points, proxy minus About page)")
    ax.set_title("Which document type is gaining ground on each theme?", loc="left", fontsize=14)
    ax.spines[["top", "right"]].set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in ["#7b4bc4", "#e8590c", "#9e9e9e"]]
    ax.legend(handles, ["Proxies gaining", "About pages gaining", "No clear trend"], frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(VISUALIZATIONS / "gap_trends.png", dpi=150)
    plt.close(fig)


def main():
    """Measure how the gap between proxies and About pages changed for each theme, and save the tables and chart."""
    FINAL.mkdir(parents=True, exist_ok=True)
    VISUALIZATIONS.mkdir(exist_ok=True)
    trends = trend_table()
    trends.to_csv(FINAL / "gap_trends.csv", index=False)
    sectors = sector_table()
    sectors.to_csv(FINAL / "gap_by_sector.csv", index=False)
    plot(trends)
    print(trends.to_string(index=False))
    print(f"\nWithin-company gap change per year, by sector:\n{sectors.to_string(index=False)}")


main()
