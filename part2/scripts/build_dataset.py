from pathlib import Path

import pandas as pd

PART2 = Path(__file__).resolve().parent.parent
OUTPUT = PART2 / "data" / "output"
FINAL = PART2 / "data" / "final"

THEMES = ["integrity", "innovation", "customer", "collaboration", "diversity_inclusion",
          "performance", "adaptability", "community", "safety", "sustainability"]
TONE = ["tone_positive", "tone_negative", "tone_uncertainty"]
COLUMNS = ["ticker", "company_name", "sector", "year", *THEMES, *TONE]


def main():
    """Join company details with the theme and tone scores into final_dataset.csv."""
    df = pd.read_csv(OUTPUT / "proxy_index.csv").merge(pd.read_csv(OUTPUT / "text_nlp_mining.csv"), on=["ticker", "year"])

    FINAL.mkdir(exist_ok=True)
    df[COLUMNS].sort_values(["ticker", "year"]).to_csv(FINAL / "final_dataset.csv", index=False)
    print(f"Saved {len(df)} rows and {len(COLUMNS)} columns to data/final/final_dataset.csv")


main()
