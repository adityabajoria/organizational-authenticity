import pandas as pd

from wayback import DATA, YEARS, is_usable, query_cdx


def usable_per_year(captures):
    return {year: sum(1 for c in captures
                      if c["timestamp"].startswith(str(year)) and is_usable(c))
            for year in YEARS}


def main():
    companies = pd.read_csv(DATA / "companies_final.csv")
    matrix = {}

    for i, co in companies.iterrows():
        print(f"[{i + 1:2d}/{len(companies)}] {co.ticker}", flush=True)
        matrix[co.ticker] = usable_per_year(query_cdx(co.about_url))

    matrix = pd.DataFrame.from_dict(matrix, orient="index")
    matrix.index.name = "ticker"
    matrix.to_csv(DATA / "coverage_matrix.csv")

    covered = (matrix > 0).sum().sum()
    print(f"\nCompany-years with a usable capture: {covered}/{matrix.size} "
          f"({covered / matrix.size:.0%})")


main()
