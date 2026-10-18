## What I did

1. **Index** (`build_index.py`): for every company-year with both an About page (Part 1) and a proxy (Part 2), I scored how well the proxy backs up the values the About page claims.
   - Each proxy's emphasis on each theme is ranked against companies in the same sector and year, giving a percentile.
   - **`authenticity_index`** = the average percentile of the themes the About page claims, minus the average percentile of all 10 themes. Above 0 means the proxy emphasises the claimed values more than its other topics; below 0 means it emphasises them less.
   - **`authenticity_percentile`** = where that score ranks among all company-years, from 0 to 1.
2. **Validation** (`validate_index.py`): tested whether the index is meaningful, compared it with two simpler versions, and summarised it by sector, year and company (`data/output/index_by_company.csv`). This made sure the results actually made sense.

## Why

Three ideas shaped how I built the index.

- **Alignment:** a company's formal disclosures emphasise the values it publicly claims more than other topics.
- **Comparing within sectors:** industries naturally talk about different things (energy companies about safety, banks about clients), so each company is compared only with its peers.
- **Subtracting the company's own average:** some proxies discuss every value at length, which would make any claim look backed up. My first version mostly measured this, so I adjusted for each company's overall level.

## Final Dataset

Each row of `data/final/final_dataset.csv` is one company-year (`ticker`, `company_name`, `sector`, `year`). It lists the themes the About page claims (`theme`) and how many (`number_of_themes`), followed by the score: `authenticity_index`, from -100 to 100, and `authenticity_percentile`, its rank among all company-years from 0 to 1.

## Validity checks

These checks test whether the index measures real alignment, rather than chance or how much a proxy discusses values overall.

- **Shuffle test:** pairing each proxy with another company's About page gives clearly lower scores than the real pairs, so the index captures company-specific alignment rather than chance.
- **Theme check:** for most themes, companies that claim a theme emphasise it more in their proxy than companies that do not.
- **Wordiness check:** the final index is unrelated to how values-heavy a proxy is overall, unlike the first version.

## Assumptions

- Part 1's theme labels capture what a company claims, and Part 2's theme scores capture what its proxy emphasises.
- Emphasis relative to sector peers, and to the company's own average, is a fair test of alignment.

## What I would do differently with more time

- Give less weight to themes whose keywords were less accurate in Part 2.
- Compare each company with its own history (did its disclosures follow a new claim?) as well as with peers.

## Known limitations

- The index can only be calculated where Part 1 has a usable About page, so earlier years include fewer companies.
- The signal is small and varies from year to year, so single-year differences between companies are not meaningful.
