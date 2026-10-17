from pathlib import Path

import numpy as np
import pandas as pd

PART3 = Path(__file__).resolve().parent.parent
FINAL = PART3 / "data" / "final" / "final_dataset.csv"
OUTPUT = PART3 / "data" / "output"
PROXY = PART3.parent / "part2" / "data" / "final" / "final_dataset.csv"

THEMES = ["integrity", "innovation", "customer", "collaboration", "diversity_inclusion",
          "performance", "adaptability", "community", "safety", "sustainability"]
VERSIONS = {
    "vs_all_companies": ("year", False),
    "vs_sector": (["year", "sector"], False),
    "vs_sector_adjusted (final)": (["year", "sector"], True),
}
SHUFFLES = 1000


def percentiles(proxies, groups):
    """Rank each proxy's emphasis on every theme against its peer group (0-1)."""
    return proxies.set_index(["ticker", "year"]).groupby(groups)[THEMES].rank(pct=True)


def scores(df, pct, stated, adjust):
    """Score each company-year on its stated themes, optionally relative to its own average theme."""
    rows = [pct.loc[(t, y)] for t, y in zip(df.ticker, df.year)]
    return np.array([100 * (r[s].mean() - (r.mean() if adjust else 0)) for r, s in zip(rows, stated)])


def shuffle_test(df, pct, adjust):
    """Compare real scores with scores built from other companies' About pages in the same year."""
    rng = np.random.default_rng(0)
    real = scores(df, pct, df.stated_themes.str.split(";"), adjust).mean()
    shuffled = [scores(df, pct, df.groupby("year").stated_themes
                       .transform(lambda s: rng.permutation(s.values)).str.split(";"), adjust).mean()
                for _ in range(SHUFFLES)]
    return round(real, 1), round(np.mean(shuffled), 1), np.mean(np.array(shuffled) >= real)


def themes_passed(df, pct, adjust):
    """Count themes that get more proxy emphasis when the About page states them."""
    rows = [pct.loc[(t, y)] for t, y in zip(df.ticker, df.year)]
    passed = 0
    for theme in THEMES:
        stated = df.stated_themes.str.split(";").map(lambda s: theme in s).values
        p = np.array([r[theme] - (r.mean() if adjust else 0) for r in rows])
        passed += p[stated].mean() > p[~stated].mean()
    return passed


def year_ranges(years):
    """Write a list of years compactly, e.g. 2016-2019, 2022-2024."""
    years, parts, start = sorted(years), [], None
    for i, y in enumerate(years):
        start = y if start is None else start
        if i == len(years) - 1 or years[i + 1] != y + 1:
            parts.append(str(y) if start == y else f"{start}-{y}")
            start = None
    return ", ".join(parts)


def main():
    """Compare the three index versions on validity, then summarise the final index."""
    df = pd.read_csv(FINAL)
    proxies = pd.read_csv(PROXY)
    checks = []

    for name, (groups, adjust) in VERSIONS.items():
        pct = percentiles(proxies, groups)
        s = scores(df, pct, df.stated_themes.str.split(";"), adjust)
        verbosity = np.array([pct.loc[(t, y)].mean() for t, y in zip(df.ticker, df.year)])
        real, shuffled, p = shuffle_test(df, pct, adjust)
        prev = pd.Series(s, index=df.index).groupby(df.ticker).shift()
        checks.append({"version": name, "mean": round(s.mean(), 1), "sd": round(s.std(), 1),
                       "shuffled_mean": shuffled, "shuffle_p": p,
                       "themes_passed": f"{themes_passed(df, pct, adjust)}/10",
                       "stability": round(pd.Series(s).corr(prev.reset_index(drop=True)), 2),
                       "corr_with_verbosity": round(np.corrcoef(s, verbosity)[0, 1], 2)})

    print(pd.DataFrame(checks).to_string(index=False))

    index = df.authenticity_index
    print(f"\nFinal index: mean {index.mean():.1f}, sd {index.std():.1f}, "
          f"min {index.min()}, max {index.max()}, positive in {100 * (index > 0).mean():.0f}% of company-years")
    print(f"\nBy sector:\n{df.groupby('sector').authenticity_index.mean().round(1).sort_values().to_string()}")
    print(f"\nBy year:\n{df.groupby('year').authenticity_index.mean().round(1).to_string()}")

    grouped = df.groupby(["ticker", "sector"])
    companies = pd.DataFrame({"years": grouped.year.agg(year_ranges),
                              "avg_authenticity_index": grouped.authenticity_index.mean().round(1)})
    companies = companies[grouped.size() >= 3].sort_values("avg_authenticity_index")
    companies.to_csv(OUTPUT / "index_by_company.csv")
    print(f"\nLowest:\n{companies.head(5).to_string()}\n\nHighest:\n{companies.tail(5).to_string()}")


main()
