import json
import os
import time
from difflib import SequenceMatcher

import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types
from wayback import DATA, PART1

MODEL = "gemini-3.5-flash-lite"
CHANGE_THRESHOLD = 0.98
MAX_WORDS = 2000
CACHE = DATA / "llm_cache"

THEMES = {
    "integrity": "Honesty, ethics, transparency, trust, accountability.",
    "innovation": "New ideas, technology, research, creativity, invention.",
    "customer": "Customer needs, satisfaction, service, experience, loyalty.",
    "collaboration": "Teamwork, cooperation, partnerships, communication, shared goals.",
    "diversity_inclusion": "Diversity, equity, inclusion, belonging, equal opportunity.",
    "performance": "Results, growth, profitability, efficiency, shareholder value.",
    "adaptability": "Agility, flexibility, resilience, change, responsiveness.",
    "community": "Social impact, philanthropy, volunteering, community development, social responsibility.",
    "safety": "Health, safety, well-being, protection, risk prevention.",
    "sustainability": "Environment, climate, emissions, conservation, renewable energy."
}

load_dotenv(PART1 / ".env")
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def call_llm(prompt, cache_name):
    path = CACHE / f"{cache_name}.json"
    if path.exists():
        return json.loads(path.read_text())

    config = types.GenerateContentConfig(temperature=0, response_mime_type="application/json")
    for attempt in range(5):
        try:
            time.sleep(5)
            response = client.models.generate_content(model=MODEL, contents=prompt, config=config)
            result = json.loads(response.text)
            break
        except Exception as e:
            print(f"    error ({str(e)[:60]}), retrying in 20s", flush=True)
            time.sleep(20)
    else:
        raise RuntimeError(f"Gave up on {cache_name}")

    CACHE.mkdir(exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    return result


def shorten(text, max_words=MAX_WORDS):
    return " ".join(text.split()[:max_words])


def add_change_columns(df):
    df = df.sort_values(["ticker", "year"]).reset_index(drop=True)
    df["similarity_to_prior"] = None
    df["changed_from_prior"] = None
    for i in range(1, len(df)):
        if df.loc[i, "ticker"] == df.loc[i - 1, "ticker"]:
            sim = SequenceMatcher(None, df.loc[i - 1, "page_text_clean"],
                                  df.loc[i, "page_text_clean"]).ratio()
            df.loc[i, "similarity_to_prior"] = round(sim, 3)
            df.loc[i, "changed_from_prior"] = sim < CHANGE_THRESHOLD
    return df


def get_themes(row):
    theme_list = "\n".join(f"- {name}: {desc}" for name, desc in THEMES.items())
    prompt = f"""You are coding a company's "About Us" page for research on stated corporate values.

Categories:
{theme_list}

Which categories does this page clearly express as something the company values?
Use only the category names above. For each one, give a short exact quote from the page.
Return JSON like: {{"innovation": "quote", "customer": "quote"}}

{row.company_name} ({row.year}):
{shorten(row.page_text_clean)}"""
    result = call_llm(prompt, f"{row.ticker}_{row.year}")
    return {k: v for k, v in result.items() if k in THEMES}


def get_shifts(ticker, company, rows):
    pages = "\n\n".join(f"=== {r.year} ===\n{shorten(r.page_text_clean, 1200)}"
                        for r in rows.itertuples())
    prompt = f"""Below are yearly snapshots of {company}'s "About Us" page.

Describe notable changes in language over time: themes added or dropped, tone,
vocabulary, length. Only mention years where something changed.
Return JSON like: {{"2019": "note", "2021": "note"}}

{pages}"""
    return call_llm(prompt, f"{ticker}_shifts")


def main():
    df = pd.read_csv(DATA / "extracted.csv")
    df = df[(df.status == "ok") & ~df.flag_too_short.astype(bool) & ~df.flag_archive_error.astype(bool)]
    df = add_change_columns(df)
    print(f"{len(df)} snapshots to analyse")

    themes, notes = [], []
    for ticker, rows in df.groupby("ticker", sort=False):
        print(ticker, flush=True)
        shifts = get_shifts(ticker, rows.company_name.iloc[0], rows)
        for row in rows.itertuples():
            found = get_themes(row)
            themes.append(";".join(sorted(found)))
            notes.append(shifts.get(str(row.year), ""))

    df["theme_categories"] = themes
    df["analyst_notes"] = notes
    df.to_csv(DATA / "llm_results.csv", index=False)
    print(f"Saved {len(df)} rows to data/llm_results.csv")


main()
