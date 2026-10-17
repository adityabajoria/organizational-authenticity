## What I did

1. **Coverage** (`cdx_coverage.py`): found an About page URL for each company (`companies_final.csv`) and counted archived captures per year (2016–2024) with the Wayback Machine CDX API. For 8 companies that moved their page, I found older URLs (`find_historical_urls.py`, `url_timeline.csv`).
2. **Snapshots** (`select_and_fetch.py`): downloaded one capture per company-year, 334 of 450. The 116 gaps are 103 years with no capture, 8 with no archived URL and 5 failed downloads; each is explained in `analyst_notes`.
3. **Text** (`extract_text.py`): removed menus, footers, banners and code; excluded 35 pages (34 under 75 words, 1 error page), leaving 299.
4. **LLM** (`llm_analysis.py`, Gemini `gemini-3.5-flash-lite`, temperature 0):
   - `changed_from_prior`: text similarity below 98% vs the previous usable year (no LLM)
   - `theme_categories`: themes each page expresses, with a supporting quote (saved in `llm_cache/`)
   - `analyst_notes`: one call per company comparing all its years
5. **Dataset** (`build_dataset.py`): `data/final/final_dataset.csv`, 450 rows. Responses are cached in `llm_cache/` for reproducibility.

## Why

- **July 1** is mid-year, so the snapshot best represents that year.
- **Themes:** `integrity`, `innovation`, `customer`, `collaboration`, `diversity_inclusion`, `performance`, `adaptability` come from MIT SMR's Culture 500 "Big Nine" values (Sull & Sull et al., 2019); `community`, `safety`, `sustainability` were added for ESG relevance. All 10 are reused in Part 2 for comparison in Part 3.

## Assumptions

- The capture closest to July 1 (before or after, same year only) represents the year; median distance is 7 days.
- A company's About page reflects its stated values.
- Text differences under 2% are noise (dates, typo fixes).

## What I would do differently with more time

- Find alternative URLs for gap-heavy companies (CRM, ABBV, AXP, C) and track URL changes from the start.
- Split long pages into chunks instead of truncating at 2,000 words.
- Validate Gemini's labels against a hand-coded sample.

## Known limitations

- Coverage is uneven: 17 usable pages in 2016 vs 45 in 2024.
- Some pages are imperfect stand-ins: NVDA and EOG (careers pages), PSX (homepage), UNH (uhc.com).
- Gemini reads only the first 2,000 words of each page (affects BRK.B).
