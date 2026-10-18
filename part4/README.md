## What I did

I compared, theme by theme and year by year, how often companies discuss each of the 10 values themes on their About Us pages (Part 1) versus in their proxy statements (Part 2), and tested whether the gap between the two is really changing.

1. **Comparison** (`theme_comparison.py`): for every company-year with both an About page and a proxy, I marked whether each document discusses each theme. For About pages, the theme is one Gemini identified on the page; for proxies, the theme appears in at least 1% of the proxy's sentences. I then calculated the share of companies discussing each theme in each document type every year (`data/final/theme_by_year.csv`, summarised in `theme_summary.csv`).
2. **Visualizations** (`plot_themes.py`): one chart per theme with an About Us line and a proxy line from 2016 to 2024, marking where the lines cross or, if they never cross, each line's highest and lowest points. `visualizations/all_themes.png` shows all 10 themes side by side.
3. **Gap analysis** (`gap_analysis.py`): for each company, theme and year, I measured the gap between its proxy and its About page, then estimated how that gap changed per year **within the same companies**, so results are not driven by companies entering the sample later. I tested whether each trend is statistically clear, repeated it with stricter and looser proxy thresholds (0.5% and 2%), and repeated it within each sector (`gap_trends.csv`, `gap_by_sector.csv`, `visualizations/gap_trends.png`).

## What I found

- **Proxies are gaining ground on sustainability and innovation**, and this holds at every threshold. Within the same companies, sustainability moved from being discussed equally in both documents to being far more present in proxies; innovation, once mainly a website theme, is catching up in proxies.
- **Community, adaptability and collaboration** also shifted towards proxies, but these trends depend on the threshold, so they are weaker evidence.
- **Diversity and inclusion, integrity, safety, performance and customer** show no clear change in the gap: both documents moved together, or the change was too small to separate from noise. For diversity, website mentions rose and then fell after 2022, but within the same companies the gap between the two documents did not change clearly.
- **By sector**, the shift on sustainability comes mainly from Consumer Discretionary and Healthcare companies; Energy companies already discussed sustainability in both documents, so their gap barely changed.

Overall, formal disclosures have taken over some values themes, most clearly sustainability, while others moved in step across both documents. This helps explain the modest alignment found in Part 3: the two channels evolve differently, theme by theme.

## Why

- Parts 1 and 2 measure each document type separately, and Part 3 compares them one year at a time. Looking at how the gap changes over time shows *which* themes are drifting apart and which move together.
- Using the same unit for both documents, the share of companies discussing a theme, makes them directly comparable.
- Measuring trends within the same companies, and checking several thresholds, separates real shifts from changes in the sample or in the measurement choice.

## Assumptions

- A theme appearing in at least 1% of a proxy's sentences means the proxy genuinely discusses it, rather than mentioning it in passing.
- Gemini's theme labels from Part 1 reflect whether an About page discusses a theme.
- A straight-line trend is a reasonable summary of how each gap changed over nine years.

## What I would do differently with more time

- Link turning points (for example, the drop in website diversity language) to specific events, such as regulatory changes or shareholder campaigns.
- Look at individual companies with the largest gaps to understand what drives them.
- Use Gemini on proxies, as in Part 1, so both documents are labelled the same way.

## Known limitations

- The two documents are measured differently (Gemini labels for About pages, keyword counts for proxies), so the size of the gap depends partly on the method; trends over time are more reliable than the gap itself.
- Earlier years include fewer companies, so estimates before 2019 are less precise.
- Diversity keywords in proxies are broad (for example, board diversity), which pushes that line close to 100%.
- The results show associations over time, not the reasons behind them.
