import json

import pandas as pd

from wayback import DATA

CACHE = DATA / "llm_cache"

COLUMNS = [
    "ticker", "company_name", "sector", "year", "page_text_clean",
    "changed_from_prior", "theme_categories", "analyst_notes",
    "status", "gap_reason", "compared_to_year", "similarity_to_prior",
    "word_count", "extraction_method", "snapshot_date", "about_url",
    "wayback_url", "theme_evidence",
]

GAP_NOTES = {
    "no_captures_in_year": "No usable Wayback capture of the About page in this year.",
    "no_archived_url_for_year": "No archived About page URL exists for this year.",
    "fetch_failed": "Captures exist but none could be downloaded from the archive.",
    "text_too_short": "Archived page had under 75 words of text after cleaning.",
    "archived_error_page": "Archived capture is the company's error page, not the About page.",
}


def load_evidence(row):
    path = CACHE / f"{row.ticker}_{row.year}.json"
    if row.status != "ok" or not path.exists():
        return ""
    return json.dumps(json.loads(path.read_text()), ensure_ascii=False)


def label_status(df):
    too_short = (df.status == "ok") & df.flag_too_short.fillna(False).astype(bool)
    error_page = (df.status == "ok") & df.flag_archive_error.fillna(False).astype(bool)
    df.loc[too_short, "gap_reason"] = "text_too_short"
    df.loc[error_page, "gap_reason"] = "archived_error_page"
    df.loc[too_short | error_page, "status"] = "excluded"
    return df


def add_prior_year(df):
    analysed = df[df.status == "ok"].sort_values(["ticker", "year"])
    prior = analysed.groupby("ticker").year.shift()
    df["compared_to_year"] = prior.reindex(df.index).astype("Int64")
    return df


def fill_notes(row):
    if row.status != "ok":
        return GAP_NOTES[row.gap_reason]
    if isinstance(row.analyst_notes, str) and row.analyst_notes:
        return row.analyst_notes
    if pd.isna(row.compared_to_year):
        return "First usable year; no prior snapshot to compare."
    if not row.changed_from_prior:
        return f"No change from {row.compared_to_year}."
    return f"Text changed from {row.compared_to_year}; no notable language shift identified."


def main():
    base = pd.read_csv(DATA / "extracted.csv")
    llm = pd.read_csv(DATA / "llm_results.csv")[
        ["ticker", "year", "similarity_to_prior", "changed_from_prior",
         "theme_categories", "analyst_notes"]]

    df = base.merge(llm, on=["ticker", "year"], how="left")
    df = label_status(df)
    df = add_prior_year(df)
    df["theme_evidence"] = df.apply(load_evidence, axis=1)
    df["analyst_notes"] = df.apply(fill_notes, axis=1)
    df["theme_categories"] = df.theme_categories.fillna("")

    df = df[COLUMNS].sort_values(["ticker", "year"])
    df.to_csv(DATA / "part1_dataset.csv", index=False)

    print(f"Saved {len(df)} rows to data/part1_dataset.csv")
    print(df.status.value_counts().to_string())
    print(df.gap_reason.value_counts().to_string())


main()
