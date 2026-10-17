import re
from pathlib import Path

import pandas as pd

PART2 = Path(__file__).resolve().parent.parent
INPUT = PART2 / "data" / "input"
OUTPUT = PART2 / "data" / "output"
CLEAN = OUTPUT / "clean_text"

SAMPLE_PER_THEME = 25

THEMES = {
    "integrity": ["integrity", "ethic*", "honest*", "transparen*", "accountab*", "code of conduct"],
    "innovation": ["innovat*", "invent*", "breakthrough*", "research and development", "cutting-edge", "creativity"],
    "customer": ["customer*", "client*", "consumer*"],
    "collaboration": ["collaborat*", "teamwork", "partnership*", "cooperat*", "work together", "one team"],
    "diversity_inclusion": ["diversity", "diverse", "inclusion", "inclusive", "racial", "ethnic*", "gender",
                            "women", "underrepresented", "minorit*", "belonging", "equal opportunity"],
    "performance": ["shareholder value", "profitab*", "growth", "financial results", "efficien*", "productivity"],
    "adaptability": ["agile", "agility", "adapt*", "flexib*", "resilien*", "nimble", "transform*"],
    "community": ["communit*", "philanthrop*", "volunteer*", "charit*", "nonprofit*", "social impact",
                  "social responsibility"],
    "safety": ["safety", "injur*", "fatalit*", "well-being", "wellbeing", "wellness", "occupational health"],
    "sustainability": ["sustainab*", "climate", "emission*", "greenhouse", "carbon", "renewable",
                       "environmental", "net zero", "biodiversity", "decarboni*"],
}


def to_pattern(terms):
    """Turn a readable word list into one case-insensitive whole-word regex."""
    parts = [r"[\s-]".join(re.escape(w).replace(r"\*", r"\w*") for w in t.replace("-", " ").split())
             for t in terms]
    return re.compile(rf"\b({'|'.join(parts)})\b", re.IGNORECASE)


PATTERNS = {name: to_pattern(terms) for name, terms in THEMES.items()}
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“(])")


def split_sentences(text):
    """Split text into sentences, dropping fragments under 5 words."""
    return [s for s in SENTENCE_END.split(" ".join(text.split())) if len(s.split()) >= 5]


def load_tone_words():
    """Load the Loughran-McDonald word lists as {category: set of words}."""
    lm = pd.read_csv(INPUT / "lm_word_lists.csv")
    return {cat: set(words) for cat, words in lm.groupby("category").word}


def tone(text, tone_words):
    """Return the % of words in each Loughran-McDonald category."""
    words = re.findall(r"[a-z]+", text.lower())
    return {f"tone_{cat}": round(100 * sum(w in lst for w in words) / len(words), 3)
            for cat, lst in tone_words.items()}


def theme_hits(sentences):
    """Return the sentences that mention each theme."""
    return {name: [s for s in sentences if p.search(s)] for name, p in PATTERNS.items()}


def main():
    """Score every proxy on themes and tone, and save a spot-check sample."""
    index = pd.read_csv(OUTPUT / "extracted.csv")
    tone_words = load_tone_words()
    rows, matches = [], []

    for p in index.itertuples():
        text = (CLEAN / p.ticker / f"{p.year}.txt").read_text()
        sentences = split_sentences(text)
        row = {"ticker": p.ticker, "year": p.year}

        for name, hits in theme_hits(sentences).items():
            row[name] = round(100 * len(hits) / len(sentences), 3)
            matches += [{"theme": name, "ticker": p.ticker, "year": p.year, "sentence": s[:400]} for s in hits]
        rows.append({**row, **tone(text, tone_words)})
        print(f"{p.ticker} {p.year}", flush=True)

    pd.DataFrame(rows).to_csv(OUTPUT / "text_mining.csv", index=False)
    sample = pd.DataFrame(matches).groupby("theme").sample(SAMPLE_PER_THEME, random_state=0)
    sample.assign(correct="").to_csv(OUTPUT / "spot_check_sample.csv", index=False)
    print(f"\nSaved {len(rows)} rows to data/output/text_mining.csv")


main()
