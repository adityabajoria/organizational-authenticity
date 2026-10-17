# Part 1: Stated Values

## What I did

I first manually found an About page URL for each of the 50 companies (`companies_final.csv`). Using `01_cdx_coverage.py` (with shared helpers in `wayback.py`), I queried the Wayback Machine CDX API for every archived capture of each page from 2016 to 2024 and recorded the number of usable captures per company-year in `coverage_matrix.csv`.

Many company-years had no usable capture at the original URL, mostly because some companies had moved their About page. For those 8 companies, I searched the archive for their older URLs (`01b_find_historical_urls.py`) and recorded which URL applies in which years in `url_timeline.csv`. I then selected and downloaded one snapshot per company-year (`02_select_and_fetch.py`). In total I collected 334 of 450 snapshots.

Next, I extracted the visible body text from each page (`03_extract_text.py`), removing menus, footers, cookie banners, buttons and leftover code. I excluded 35 pages: 34 had fewer than 75 words after cleaning, and 1 was an archived error page. This left 299 usable pages.

I then analysed the 299 usable pages with the Google Gemini API (`04_llm_analysis.py`, model `gemini-3.5-flash-lite`, temperature 0 for consistent answers):

- **Changed from prior year:** decided without the LLM, by comparing each page's text with the company's previous usable year. Pages less than 98% similar count as changed.
- **Themes:** I defined 10 value themes (see [Why](#why)). For each page, Gemini was given the themes and their definitions, and asked which themes the page clearly expresses, with an exact supporting quote for each (`theme_evidence`).
- **Comparisons:** I called Gemini once per company with all its years side by side and asked what changed over time in themes, tone, vocabulary and length (`analyst_notes`).

All responses are cached in `llm_cache/`, so the results can be reproduced without new API calls.

Finally, I combined everything into `part1_dataset.csv` (`05_build_dataset.py`): 450 rows, one per company-year, with the required columns plus `status`, `gap_reason`, `snapshot_date`, `wayback_url` and `theme_evidence`.

## Why

- **July 1:** it is the middle of the year, so the snapshot best represents the page as it stood that year.
- **Themes:** `integrity`, `innovation`, `customer`, `collaboration`, `diversity_inclusion`, `performance`, `adaptability`, `community`, `safety`, `sustainability`.

  7 of my 10 themes come from MIT Sloan Management Review's Culture 500 "Big Nine" values (Sull & Sull et al., 2019), which were identified from 600+ company websites. I added `community`, `safety` and `sustainability` because they are central to ESG disclosure, and I reuse all 10 in Part 2 so the two parts can be compared directly in Part 3.

## Assumptions

- For each year, I used the capture closest to July 1, either before or after it, and never used a capture from a different year. Searching in both directions gave the best chance of finding a capture; the median snapshot is 7 days from July 1.
- A company's About page reflects its stated values.
- One snapshot per year is enough to represent the page for that year.
- Differences below 2% (e.g. dates, typo fixes) are noise, not real changes.

## What I would do differently with more time

- Find alternative URLs for the companies with the most gaps (e.g. CRM, ABBV, AXP, C), which would reduce missing values.
- Track URL changes systematically for every company from the start, rather than only after noticing gaps in the coverage matrix.
- Split long pages into smaller chunks for the LLM instead of cutting them off at 2,000 words.
- Check Gemini's theme labels against a small hand-coded sample to measure their accuracy.
