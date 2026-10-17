import pandas as pd

from wayback import DATA

CLEAN = DATA / "clean_text"

COLUMNS = [
    "ticker", "company_name", "sector", "year", "page_text_clean",
    "changed_from_prior", "theme_categories", "analyst_notes", "status",
]

GAP_NOTES = {
    "no_captures_in_year": "No usable Wayback capture of the About page in this year.",
    "no_archived_url_for_year": "No archived About page URL exists for this year.",
    "fetch_failed": "Captures exist but none could be downloaded from the archive.",
    "text_too_short": "Archived page had under 75 words of text after cleaning.",
    "archived_error_page": "Archived capture is the company's error page, not the About page.",
}


def load_text(row):
    if row.status != "ok":
        return ""
    return " ".join((CLEAN / row.ticker / f"{row.year}.txt").read_text().split())


def label_status(df):
    too_short = df.flag_too_short.fillna(False).astype(bool)
    error_page = df.flag_archive_error.fillna(False).astype(bool)
    df.loc[too_short, "gap_reason"] = "text_too_short"
    df.loc[error_page, "gap_reason"] = "archived_error_page"
    df.loc[too_short | error_page, "status"] = "excluded"
    return df


def prior_years(df):
    analysed = df[df.status == "ok"].sort_values(["ticker", "year"])
    return analysed.groupby("ticker").year.shift().reindex(df.index).astype("Int64")


def fill_notes(row):
    if row.status != "ok":
        return GAP_NOTES[row.gap_reason]
    if isinstance(row.analyst_notes, str) and row.analyst_notes:
        return row.analyst_notes
    if pd.isna(row.prior_year):
        return "First usable year; no prior snapshot to compare."
    if not row.changed_from_prior:
        return f"No change from {row.prior_year}."
    return f"Text changed from {row.prior_year}; no notable language shift identified."


def main():
    df = pd.read_csv(DATA / "snapshot_index.csv")
    df = df.merge(pd.read_csv(DATA / "extracted.csv"), on=["ticker", "year"], how="left")
    df = df.merge(pd.read_csv(DATA / "llm_results.csv"), on=["ticker", "year"], how="left")

    df = label_status(df)
    df["prior_year"] = prior_years(df)
    df["page_text_clean"] = df.apply(load_text, axis=1)
    df["analyst_notes"] = df.apply(fill_notes, axis=1)
    df.loc[(df.status == "ok") & df.prior_year.isna(), "changed_from_prior"] = "FIRST_YEAR"

    df = df[COLUMNS].replace("", None).fillna("MISSING").sort_values(["ticker", "year"])
    df.to_csv(DATA / "part1_dataset.csv", index=False)

    print(f"Saved {len(df)} rows to data/part1_dataset.csv")
    print(df.status.value_counts().to_string())


main()
