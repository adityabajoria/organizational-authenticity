import re
import warnings
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

PART2 = Path(__file__).resolve().parent.parent
OUTPUT = PART2 / "data" / "output"
RAW = OUTPUT / "raw_proxies"
CLEAN = OUTPUT / "clean_text"

BLOCK_TAGS = ["p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "br"]
MIN_TABLE_WORD_SHARE = 0.5
WORD = re.compile(r"[A-Za-z]{3,}")


def word_share(text):
    """Return the share of tokens that are real words (3+ letters)."""
    tokens = text.split()
    return sum(bool(WORD.search(t)) for t in tokens) / max(len(tokens), 1)


def drop_numeric_tables(soup):
    """Delete tables that are mostly numbers, keeping tables that hold text."""
    for table in soup("table"):
        if not table.decomposed and word_share(table.get_text(" ")) < MIN_TABLE_WORD_SHARE:
            table.decompose()


def extract(html):
    """Turn a proxy's HTML into clean text, one line per block, without duplicates."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "ix:header"]):
        tag.decompose()
    drop_numeric_tables(soup)
    for tag in soup(BLOCK_TAGS):
        tag.insert_after("\n")
    for cell in soup(["td", "th"]):
        cell.insert_after(" ")

    seen, lines = set(), []
    for line in soup.get_text().splitlines():
        line = " ".join(line.split())
        if WORD.search(line) and line.lower() not in seen:
            seen.add(line.lower())
            lines.append(line)
    return "\n".join(lines)


def main():
    """Extract text from every proxy; write extracted.csv with word counts."""
    index = pd.read_csv(OUTPUT / "proxy_index.csv")
    rows = []

    for p in index.itertuples():
        html = (RAW / p.ticker / f"{p.year}.htm").read_bytes().decode("utf-8", errors="replace")
        text = extract(html)

        out_path = CLEAN / p.ticker / f"{p.year}.txt"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text)
        rows.append({"ticker": p.ticker, "year": p.year, "word_count": len(text.split())})
        print(f"{p.ticker} {p.year}: {rows[-1]['word_count']} words", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT / "extracted.csv", index=False)
    print(f"\nExtracted {len(df)} proxies, median {df.word_count.median():.0f} words")


main()
