"""
Signal Room content engine
===========================

What this does
---------------
Once a day, this script asks Claude to research ten AI-news categories,
pick the single most important real story in each one, and write it up
in plain language for a general audience. It saves the result as
signal_room_data.json, which the dashboard (signal-room.html) can load
and display.

How to run it yourself
------------------------
1. Get an API key from console.anthropic.com (Anthropic's developer
   platform, separate from a normal claude.ai account).
2. Install the one dependency:  pip install anthropic
3. Set the key as an environment variable:
      export ANTHROPIC_API_KEY="sk-ant-...";
4. Run:  python content_engine.py
   It writes signal_room_data.json in the same folder.

How to make it run automatically, once a day, for free
---------------------------------------------------------
Put this script in a GitHub repository, then add a GitHub Action
(a small robot that runs on a schedule) that:
  a) checks out the repo
  b) runs this script (using a repo "secret" for the API key, so it's
     never visible in the code)
  c) commits the new signal_room_data.json back to the repo
  d) the dashboard, hosted for free on GitHub Pages or Vercel, reads
     that file and always shows the latest version
This is the only piece that needs to live outside "the AI world" —
a GitHub account, a scheduled trigger, and somewhere to host the page.
Everything else (the research, the writing, the judgment calls about
what matters) is handled by Claude through this script.
"""

import json
import os
from datetime import datetime, timezone
from anthropic import Anthropic

CATEGORIES = [
    ("models", "New AI models and capabilities",
     "New model releases, benchmark results, reasoning or multimodal breakthroughs"),
    ("safety", "AI safety and alignment",
     "Interpretability findings, safety research, red-teaming results, alignment concerns"),
    ("regulation", "Rules and lawmakers",
     "AI laws, government orders, international AI governance"),
    ("economy", "Jobs and the economy",
     "Automation, job losses or gains, productivity effects, economic inequality tied to AI"),
    ("geopolitics", "War and world power",
     "Autonomous weapons, military AI, the US-China AI race, AI in intelligence services"),
    ("bigtech", "Big tech and power",
     "Moves by Anthropic, OpenAI, Google DeepMind, Meta and others; who controls the leading AI systems"),
    ("energy", "Power and chips",
     "Datacentre power use, electricity grid strain, chip shortages, Nvidia and hardware news"),
    ("science", "AI in science",
     "Drug discovery, climate modelling, biology or materials-science breakthroughs made possible by AI"),
    ("disinfo", "Fake content online",
     "Deepfakes, synthetic media, AI's role in spreading false information, election-related concerns"),
    ("society", "Society and everyday life",
     "Surveillance, bias, privacy, how AI is changing daily life and human autonomy"),
]

SYSTEM_PROMPT = """You are the daily editor of Signal Room, a news dashboard about AI \
aimed at curious, non-technical readers — not engineers or AI researchers. \
Someone reading this may have never used ChatGPT or Claude before.

For the category you are given, use web search to find the single most \
important REAL news item from roughly the last 24-72 hours. Prefer items \
that are either:
  - a concrete, checkable number or event (a product launch, a law taking \
    effect, a reported figure), or
  - a notable public statement from a recognised AI leader, policymaker, \
    or researcher.

Write it up for a general reader:
  - plain, everyday words, no unexplained jargon
  - short sentences
  - if a technical term is unavoidable, explain it in the same sentence
  - never invent or approximate a quote; only include a quote you can \
    verify word-for-word from a search result, and keep it under 15 words
  - always include the real source URL you found it from

Respond with ONLY a JSON object, no other text, no markdown fences:
{
  "headline": "one sentence, sentence case, under 14 words",
  "summary": "two to three short sentences in plain language",
  "tag": "breakthrough" | "watch" | "risk",
  "source_name": "publication or organisation name",
  "source_url": "the real URL"
}
"""


def research_category(client, slug, label, hint):
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{
            "role": "user",
            "content": f"Category: {label}\nWhat this category covers: {hint}\n"
                       f"Find today's most important real story here."
        }],
    )

    text_parts = [block.text for block in message.content if block.type == "text"]
    raw = "".join(text_parts).strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {
            "headline": f"Could not parse a result for {label} today",
            "summary": "The research step returned something unexpected. Check manually.",
            "tag": "watch",
            "source_name": "",
            "source_url": "",
        }

    parsed["slug"] = slug
    parsed["category_label"] = label
    return parsed


def main():
    client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    results = []
    for slug, label, hint in CATEGORIES:
        print(f"Researching: {label} ...")
        results.append(research_category(client, slug, label, hint))

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "categories": results,
    }

    with open("signal_room_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("Wrote signal_room_data.json")


if __name__ == "__main__":
    main()
