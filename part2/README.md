## What I did

1. **Collection** (`fetch_proxies.py`): downloaded each company's annual proxy statement from SEC EDGAR for every year from 2016 to 2024, with no gaps. Where a company faced a shareholder proxy fight, I used the contested proxy instead. Links to every filing are in `data/output/proxy_index.csv`.
2. **Text** (`extract_text.py`): converted each proxy into plain text, removing tables of numbers (such as pay and vote counts) and repeated page headers so that only the written text is analysed.
3. **Text mining** (`text_nlp_mining.py`): measured how much each proxy talks about the same 10 themes as Part 1, looking specifically at the sentences that mention each theme, and measured its tone using the Loughran-McDonald finance word lists.
4. **LLM validation** (`gemini_mining.py`): used the Gemini API to check a random sample of keyword matches for each theme, to see how often the keywords really capture that theme. Overall, about 70% of matches were correct.
5. **Dataset** (`build_dataset.py`): combined the theme and tone scores into one row per company-year.

## Why

- **Proxy statements** are required every year, follow the same format across companies, and describe what companies actually reward, such as executive pay and board oversight.
- **SEC EDGAR** is the official, free source for every filing. A few companies changed their SEC identifiers over the years, so I matched them to their older ones.
- **Keyword counting** works well at this scale: the proxies are far too long to send through an LLM, and counting is fast, free and reproducible. Gemini is used where it is strongest, judging a sample.
- **Counting sentences rather than words** stops repeated boilerplate from inflating a theme.

## Evaluating Proxies

Each row of `data/final/final_dataset.csv` is one company-year (`ticker`, `company_name`, `sector`, `year`) scored on themes and tone. For each of the 10 Part 1 themes (`integrity` … `sustainability`), the score is the percentage of the proxy's sentences that contain one of the theme's keywords. Tone (`tone_positive`, `tone_negative`, `tone_uncertainty`) is the percentage of words found in the Loughran-McDonald Master Dictionary's positive, negative and uncertainty lists, which were built for financial filings and avoid misreading words like "liability" or "tax" as negative.

## Assumptions

- The more a proxy discusses a theme, the more the company emphasises it (this is later tested in Parts 3 and 4).
- The Loughran-McDonald word lists, built for financial filings, suit proxy statements.
- A small random sample per theme is enough to spot unreliable keywords.

## What I would do differently with more time

- Have Gemini check every keyword match rather than a sample, since a small sample could be unrepresentative.
- Focus Gemini on the most relevant sections, such as the shareholder letter, as in Part 1.
- Use a deep learning model (transformers) to consider the context when analysing the language.

## Known limitations

- Some themes, especially customer and diversity, pick up unrelated uses of their keywords, so their scores are likely overstated.
- The validation sample is small, so the accuracy figures are rough.
- Tone is measured word by word and ignores context (for example, "not strong" still counts as positive).
