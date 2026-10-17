import re
from pathlib import Path

import pandas as pd
import trafilatura
from bs4 import BeautifulSoup

PART1 = Path(__file__).resolve().parent.parent
DATA = PART1 / "data"
RAW = DATA / "raw_html"
CLEAN = DATA / "clean_text"

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
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(CODE_TAGS):
        tag.decompose()
    return str(soup)


def extract_trafilatura(html):
    text = trafilatura.extract(
        strip_code_blocks(html),
        favor_recall=True,
        include_comments=False,
        deduplicate=True,
    )
    return text or ""


def extract_rule_based(html):
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
    if any(re.search(p, line) for p in CODE_LINE_PATTERNS):
        return True
    letters = sum(ch.isalpha() for ch in line)
    return len(line) > 20 and letters / len(line) < 0.5


def is_menu_label(line):
    words = line.lstrip("-• ").split()
    return len(words) <= MENU_LABEL_MAX and not re.search(r"[.!?]", line)


def drop_menu_runs(lines):
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
    return len(re.findall(r"\b\w+\b", text))


def extract(html):
    text = clean_lines(extract_trafilatura(html))
    method = "trafilatura"

    if word_count(text) < MIN_WORDS:
        fallback = clean_lines(extract_rule_based(html))
        if word_count(fallback) > word_count(text):
            text, method = fallback, "rule_based_fallback"

    n = word_count(text)
    return {
        "page_text_clean": text,
        "extraction_method": method,
        "word_count": n,
        "flag_too_short": n < MIN_WORDS,
        "flag_archive_error": bool(ARCHIVE_ERROR.search(text[:500])),
    }


def main():
    index = pd.read_csv(DATA / "snapshot_index.csv")
    rows = []

    for _, snap in index.iterrows():
        row = snap.to_dict()
        html_path = RAW / snap.ticker / f"{snap.year}.html"
        if snap.status != "ok" or not html_path.exists():
            rows.append(row)
            continue

        html = html_path.read_bytes().decode("utf-8", errors="replace")
        result = extract(html)

        out_path = CLEAN / snap.ticker / f"{snap.year}.txt"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result["page_text_clean"])
        rows.append({**row, **result})

    df = pd.DataFrame(rows)
    df.drop(columns="page_text_clean").to_csv(DATA / "extracted.csv", index=False)

    ok = df[df.status == "ok"]
    print(f"Extracted {len(ok)} snapshots")
    print(ok.extraction_method.value_counts().to_string())
    print(f"Median words: {ok.word_count.median():.0f}")
    print(f"Too short: {ok.flag_too_short.sum()}")
    print(f"Archive error: {ok.flag_archive_error.sum()}")


main()
