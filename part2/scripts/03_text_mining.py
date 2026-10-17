import re
from pathlib import Path

import pandas as pd

PART2 = Path(__file__).resolve().parent.parent
INPUT = PART2 / "data" / "input"
OUTPUT = PART2 / "data" / "output"
CLEAN = OUTPUT / "clean_text"

SAMPLE_PER_THEME = 30

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
    parts = [r"[\s-]".join(re.escape(w).replace(r"\*", r"\w*") for w in t.replace("-", " ").split())
             for t in terms]
    return re.compile(rf"\b({'|'.join(parts)})\b", re.IGNORECASE)


PATTERNS = {name: to_pattern(terms) for name, terms in THEMES.items()}
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“(])")


def split_sentences(text):
    return [s for s in SENTENCE_END.split(" ".join(text.split())) if len(s.split()) >= 5]


def load_tone_words():
    lm = pd.read_csv(INPUT / "lm_word_lists.csv")
    return {cat: set(words) for cat, words in lm.groupby("category").word}


def tone(text, tone_words):
    words = re.findall(r"[a-z]+", text.lower())
    return {f"tone_{cat}": round(100 * sum(w in lst for w in words) / len(words), 3)
            for cat, lst in tone_words.items()}


def theme_shares(sentences):
    return {name: round(100 * sum(bool(p.search(s)) for s in sentences) / len(sentences), 3)
            for name, p in PATTERNS.items()}


def spot_check_sample(matches):
    sample = (pd.DataFrame(matches)
              .groupby("theme", group_keys=False)
              .apply(lambda g: g.sample(min(SAMPLE_PER_THEME, len(g)), random_state=0)))
    sample["correct"] = ""
    sample.to_csv(OUTPUT / "spot_check_sample.csv", index=False)


def main():
    index = pd.read_csv(OUTPUT / "extracted.csv")
    tone_words = load_tone_words()
    rows, matches = [], []

    for p in index.itertuples():
        text = (CLEAN / p.ticker / f"{p.year}.txt").read_text()
        sentences = split_sentences(text)
        rows.append({"ticker": p.ticker, "year": p.year, **theme_shares(sentences), **tone(text, tone_words)})

        for name, pattern in PATTERNS.items():
            for s in sentences:
                if pattern.search(s):
                    matches.append({"theme": name, "ticker": p.ticker, "year": p.year, "sentence": s[:400]})
        print(f"{p.ticker} {p.year}", flush=True)

    pd.DataFrame(rows).to_csv(OUTPUT / "text_mining.csv", index=False)
    spot_check_sample(matches)
    print(f"\nSaved {len(rows)} rows to data/output/text_mining.csv")


main()
