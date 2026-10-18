import json
import os
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types

PART2 = Path(__file__).resolve().parent.parent
OUTPUT = PART2 / "data" / "output"
CACHE = OUTPUT / "llm_cache"
MODEL = "gemini-3.5-flash-lite"

THEMES = {
    "integrity": "Honesty, ethics, transparency, trust, accountability.",
    "innovation": "New ideas, technology, research, creativity, invention.",
    "customer": "Customer needs, satisfaction, service, experience, loyalty.",
    "collaboration": "Teamwork, cooperation, partnerships, communication, shared goals.",
    "diversity_inclusion": "Diversity, equity, inclusion, belonging, equal opportunity.",
    "performance": "Results, growth, profitability, efficiency, shareholder value.",
    "adaptability": "Agility, flexibility, resilience, change, responsiveness.",
    "community": "Social impact, philanthropy, volunteering, community development, social responsibility.",
    "safety": "Health, safety, well-being, protection, risk prevention.",
    "sustainability": "Environment, climate, emissions, conservation, renewable energy."
}

load_dotenv(PART2 / ".env")
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def call_llm(prompt, cache_name):
    """Send a prompt to Gemini and return its JSON answer, using the cache if available."""
    path = CACHE / f"{cache_name}.json"
    if path.exists():
        return json.loads(path.read_text())
    config = types.GenerateContentConfig(temperature=0, response_mime_type="application/json")
    for attempt in range(5):
        try:
            result = json.loads(client.models.generate_content(model=MODEL, contents=prompt, config=config).text)
            break
        except Exception as e:
            print(f"    {type(e).__name__}, retrying", flush=True)
            time.sleep(20)
    else:
        raise RuntimeError(f"Gave up on {cache_name}")
    CACHE.mkdir(exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    return result


def judge(theme, sentences):
    """Ask Gemini whether each keyword-matched sentence is genuinely about the theme."""
    numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(sentences, 1))
    prompt = f"""Theme: {theme} ({THEMES[theme]})

Each sentence below is from a company proxy statement and contains a keyword for this theme.
For each one, answer true if the sentence is genuinely about the theme, or false if the keyword
is used in a different sense (e.g. "diversity of experience" is not about diversity and inclusion).
Return JSON like {{"1": true, "2": false}}.

{numbered}"""
    answers = call_llm(prompt, f"validate_{theme}")
    return [bool(answers.get(str(i))) for i in range(1, len(sentences) + 1)]


def main():
    """Check the spot-check sample with Gemini and report keyword precision per theme."""
    sample = pd.read_csv(OUTPUT / "spot_check_sample.csv").drop(columns="correct")
    sample["gemini_correct"] = pd.concat(
        [pd.Series(judge(theme, g.sentence.tolist()), index=g.index) for theme, g in sample.groupby("theme")])
    sample.to_csv(OUTPUT / "gemini_mining.csv", index=False)

    precision = (100 * sample.groupby("theme").gemini_correct.mean()).round(0)
    print(precision.sort_values(ascending=False).to_string())
    print(f"\nOverall: {100 * sample.gemini_correct.mean():.0f}% of keyword matches judged correct")


main()
