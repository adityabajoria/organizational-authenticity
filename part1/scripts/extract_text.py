import re

import pandas as pd
import trafilatura
from bs4 import BeautifulSoup

from wayback import OUTPUT

RAW = OUTPUT / "raw_html"
CLEAN = OUTPUT / "clean_text"

MIN_WORDS = 75
MENU_RUN_MIN = 8
MENU_LABEL_MAX = 5

CODE_TAGS = ["script", "style", "noscript", "template", "svg", "iframe"]
FALLBACK_DROP_TAGS = CODE_TAGS + ["nav", "header", "footer", "aside",
                                  "form", "button", "select", "input"]

BOILERPLATE_CLASS = re.compile(
    r"cookie|consent|banner|menu|navbar|nav-|breadcrumb|footer|header|"
    r"skip-link|modal|popup|social|share|newsletter|subscribe|search",
    re.IGNORECASE,
)
CTA_LINE = re.compile(
    r"^(learn more|read more|see more|view more|explore|discover more|"
    r"watch (the )?video|download|contact us|back to top|share|close|menu|"
    r"main menu|skip to (main )?content)\W*$",
    re.IGNORECASE,
)
FOOTER_LINE = re.compile(
    r"^(copyright\b|©|\(c\) ?\d{4}|all rights reserved)|"
    r"\b(use[sd]? cookies|cookie (policy|settings|preferences))\b",
    re.IGNORECASE,
)
ARCHIVE_ERROR = re.compile(
    r"wayback machine|got an http \d{3} response|this page is not available|"
    r"page not found|404 error|access denied|enable javascript|something has gone wrong",
    re.IGNORECASE,
)

CODE_LINE_PATTERNS = [
    r"^[\w$.]+\s*:\s*['\"\[{]",
    r"^[\w$.]+\s*:\s*(true|false|null|\d+)\s*,?$",
    r"[{;]\s*$",
    r"^\s*(/\*|@media|[#.][\w-]+[\s.{#:])",
    r"^[\s{}()\[\];,]+$",
    r"function\s*\(|=>|var |const |let |\$\(|document\.",
    r"\{\{|\}\}",
    r"</?[a-z][\w-]*[\s>/]",
    r"^[\w$.]+\(\{?$",
]


def strip_code_blocks(html):
    """Remove script, style and other non-visible tags from the HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(CODE_TAGS):
        tag.decompose()
    return str(soup)


def extract_trafilatura(html):
    """Extract the main page text with trafilatura."""
    text = trafilatura.extract(
        strip_code_blocks(html),
        favor_recall=True,
        include_comments=False,
        deduplicate=True,
    )
    return text or ""


def extract_rule_based(html):
    """Fallback extractor: strip navigation, headers, footers and other boilerplate."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(FALLBACK_DROP_TAGS):
        tag.decompose()

    page_len = len((soup.body or soup).get_text(" ", strip=True)) or 1
    to_remove = []
    for el in soup.find_all(True):
        if el.attrs is None:
            continue
        ident = " ".join(el.get("class", [])) + " " + (el.get("id") or "")
        if BOILERPLATE_CLASS.search(ident) and \
                len(el.get_text(" ", strip=True)) <= 0.5 * page_len:
            to_remove.append(el)
    for el in to_remove:
        el.decompose()

    return (soup.body or soup).get_text(separator="\n")


def looks_like_code(line):
    """Return True if a line looks like leftover code rather than text."""
    if any(re.search(p, line) for p in CODE_LINE_PATTERNS):
        return True
    letters = sum(ch.isalpha() for ch in line)
    return len(line) > 20 and letters / len(line) < 0.5


def is_menu_label(line):
    """Return True if a line is short enough to be a menu item."""
    words = line.lstrip("-• ").split()
    return len(words) <= MENU_LABEL_MAX and not re.search(r"[.!?]", line)


def drop_menu_runs(lines):
    """Remove long runs of short menu-like lines."""
    kept, run = [], []
    for line in lines + [""]:
        if line and is_menu_label(line):
            run.append(line)
            continue
        if len(run) < MENU_RUN_MIN:
            kept.extend(run)
        run = []
        if line:
            kept.append(line)
    return kept


def clean_lines(text):
    """Remove buttons, footers, code, duplicates and menus."""
    seen, kept = set(), []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if (not line
                or CTA_LINE.match(line)
                or FOOTER_LINE.search(line)
                or looks_like_code(line)
                or line.lower() in seen):
            continue
        seen.add(line.lower())
        kept.append(line)
    return "\n".join(drop_menu_runs(kept))


def word_count(text):
    """Count the words in a text."""
    return len(re.findall(r"\b\w+\b", text))


def extract(html):
    """Extract clean text, falling back to rule-based extraction if trafilatura finds too little."""
    text = clean_lines(extract_trafilatura(html))
    if word_count(text) < MIN_WORDS:
        fallback = clean_lines(extract_rule_based(html))
        if word_count(fallback) > word_count(text):
            text = fallback
    return text


def main():
    """Extract text from every snapshot; write extracted.csv with quality flags."""
    index = pd.read_csv(OUTPUT / "snapshot_index.csv")
    rows = []

    for snap in index[index.status == "ok"].itertuples():
        html = (RAW / snap.ticker / f"{snap.year}.html").read_bytes().decode("utf-8", errors="replace")
        text = extract(html)

        out_path = CLEAN / snap.ticker / f"{snap.year}.txt"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text)
        rows.append({"ticker": snap.ticker, "year": snap.year,
                     "flag_too_short": word_count(text) < MIN_WORDS,
                     "flag_archive_error": bool(ARCHIVE_ERROR.search(text[:500]))})

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT / "extracted.csv", index=False)
    print(f"Extracted {len(df)} snapshots")
    print(f"Too short: {df.flag_too_short.sum()}")
    print(f"Archive error: {df.flag_archive_error.sum()}")


main()
