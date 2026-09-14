#!/usr/bin/env python3
"""
Made From Effort — Podcast-to-post drafting routine.

Runs weekly. For each configured podcast RSS feed, finds episodes published
since the last run, transcribes them (Deepgram), and hands the transcripts
to Claude to pick the single strongest topic and draft a full Journal post
in the site's existing voice and frontmatter format.

The draft is written to posts/banked/ — NOT posts/ — so it never goes live
on its own. A human has to read it and move it into posts/ before the
existing build-journal workflow will publish it.

Usage:
    python3 scripts/podcast_to_post.py

Requires:
    pip install -r scripts/requirements-podcast.txt

Environment:
    DEEPGRAM_API_KEY   - required
    ANTHROPIC_API_KEY  - required
    ANTHROPIC_MODEL    - optional, defaults to claude-sonnet-5
"""

import glob
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import feedparser
import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(REPO_ROOT, "config", "podcasts.json")
STATE_PATH = os.path.join(REPO_ROOT, "config", "podcast_state.json")
POSTS_DIR = os.path.join(REPO_ROOT, "posts")
BANKED_DIR = os.path.join(POSTS_DIR, "banked")

DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

PLACEHOLDER_MARKERS = ("REPLACE_WITH_", "REPLACE-WITH-")


# ---------------------------------------------------------------------------
# Config / state
# ---------------------------------------------------------------------------
def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if not os.path.exists(STATE_PATH):
        return {"processed_episode_guids": []}
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    # Cap unbounded growth — keep the most recent 500 guids.
    state["processed_episode_guids"] = state["processed_episode_guids"][-500:]
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def is_placeholder(value):
    return any(marker in (value or "") for marker in PLACEHOLDER_MARKERS)


# ---------------------------------------------------------------------------
# Feed / episode discovery
# ---------------------------------------------------------------------------
def find_new_episodes(config, state):
    lookback_days = config.get("lookback_days", 10)
    max_episodes = config.get("max_episodes_per_run", 5)
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    seen = set(state.get("processed_episode_guids", []))

    candidates = []
    for feed_cfg in config.get("feeds", []):
        name = feed_cfg.get("name", "Unknown show")
        rss_url = feed_cfg.get("rss_url", "")

        if is_placeholder(rss_url) or is_placeholder(name):
            print(f"Skipping '{name}': placeholder feed config not filled in yet.")
            continue

        parsed = feedparser.parse(rss_url)
        if parsed.bozo and not parsed.entries:
            print(f"Warning: could not parse feed for '{name}' ({rss_url}): {parsed.bozo_exception}")
            continue

        for entry in parsed.entries:
            guid = entry.get("id") or entry.get("link")
            if not guid or guid in seen:
                continue

            published = entry.get("published_parsed")
            if published:
                published_dt = datetime(*published[:6], tzinfo=timezone.utc)
                if published_dt < cutoff:
                    continue
            else:
                published_dt = None

            audio_url = None
            for link in entry.get("links", []):
                if link.get("type", "").startswith("audio") or link.get("rel") == "enclosure":
                    audio_url = link.get("href")
                    break

            if not audio_url:
                print(f"Skipping episode '{entry.get('title', guid)}': no audio enclosure found.")
                continue

            candidates.append({
                "show": name,
                "guid": guid,
                "title": entry.get("title", "Untitled episode"),
                "published": published_dt,
                "audio_url": audio_url,
                "link": entry.get("link", ""),
                "summary": entry.get("summary", ""),
            })

    candidates.sort(key=lambda e: e["published"] or datetime.min.replace(tzinfo=timezone.utc))
    return candidates[:max_episodes]


# ---------------------------------------------------------------------------
# Transcription (Deepgram)
# ---------------------------------------------------------------------------
def transcribe_episode(audio_url):
    resp = requests.post(
        "https://api.deepgram.com/v1/listen",
        params={"model": "nova-2", "smart_format": "true", "punctuate": "true"},
        headers={
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"url": audio_url},
        timeout=600,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["results"]["channels"][0]["alternatives"][0]["transcript"]


# ---------------------------------------------------------------------------
# Existing posts — used as few-shot voice/format examples and for numbering
# ---------------------------------------------------------------------------
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def load_existing_posts():
    paths = sorted(glob.glob(os.path.join(POSTS_DIR, "*.md"))) + \
        sorted(glob.glob(os.path.join(BANKED_DIR, "*.md")))
    posts = []
    for path in paths:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        m = FRONTMATTER_RE.match(raw)
        if not m:
            continue
        fm_block, body = m.group(1), m.group(2)
        meta = {}
        for line in fm_block.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"').strip("'")
        meta["body"] = body.strip()
        meta["path"] = path
        posts.append(meta)
    return posts


def next_issue_number(existing_posts):
    max_issue = 0
    for p in existing_posts:
        try:
            max_issue = max(max_issue, int(p.get("issue", 0)))
        except ValueError:
            continue
    return f"{max_issue + 1:03d}"


def next_draft_date(existing_posts):
    dates = []
    for p in existing_posts:
        try:
            dates.append(datetime.strptime(p["date"], "%Y-%m-%d"))
        except (KeyError, ValueError):
            continue
    base = max(dates) if dates else datetime.now(timezone.utc).replace(tzinfo=None)
    return (base + timedelta(days=7)).strftime("%Y-%m-%d")


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


# ---------------------------------------------------------------------------
# Drafting (Claude)
# ---------------------------------------------------------------------------
DRAFT_SYSTEM_PROMPT = """You are the ghostwriter for the Made From Effort Journal — the blog at \
madefromeffort.com, run by Scott Schratwieser (Performance Edge Training + Gym Design, Long Island, NY). \
You write in his voice: direct, confident, systems-thinking, told through one real, specific story per post. \
Short punchy sentences mixed with longer ones. No hype, no vague motivational language, no fabricated facts, \
figures, or client details that were not present in the source material you were given.

You will be given one or more podcast episode transcripts. Your job:
1. Pick the single strongest, most concrete story or lesson across all the transcripts — the one that best \
fits the Journal's beat (training, gym design/build, discipline and systems, client/project stories). \
Do not try to cover everything; one sharp angle beats a broad summary.
2. Draft one full Journal post about it, matching the site's existing structure exactly.

Output ONLY a single JSON object (no markdown fences, no commentary) with these fields:
- "title": string, a direct question or bold claim, matching the tone of existing titles.
- "excerpt": string, 1-2 sentences, the RSS/email preview text.
- "cta_text": string, either "Start a Project" or "Train With Me" (pick whichever fits the post's theme).
- "tags": string, 3-5 comma-separated topical tags.
- "stats": array of 0-4 objects {"number": string, "caption": string} — ONLY include real figures actually \
stated in the transcript (a length, a dollar figure, a count, a duration). If no solid numbers exist in the \
source material, return an empty array. Never invent a number.
- "body_markdown": string, the full post body in Markdown, following this exact shape:
    - Opens with 1-3 short paragraphs setting up the hook (often a direct-answer style first line).
    - Then numbered "## 01 / <Section Title>" headers (typically 3 sections: The Mistake / What Went Wrong,
      Why It Gets Missed, The Fix — adapt titles to the actual story).
    - At least one "> pull quote" blockquote, a single punchy italic-worthy sentence pulled from or inspired
      by the point being made.
    - A numbered practical takeaway list ("What this means if you're planning ...:") of 3-5 items, each
      starting with a **bolded lead-in phrase**.
    - A short closing (1-2 paragraphs) that lands the "whole game" point.
    - Ends with a "## FAQ" section: 3-4 question/answer pairs, each question as its own **bolded line ending
      in a question mark**, followed immediately by a plain paragraph answer. This exact format is required —
      the site's build script parses it with a strict regex.

Do not include frontmatter (title/date/etc as a --- block) in body_markdown — only the Markdown body itself,
starting from the first paragraph after the (already-provided) title.
"""


def build_user_prompt(episodes, existing_posts):
    example = existing_posts[-1] if existing_posts else None
    parts = []
    if example:
        parts.append(
            "Here is one existing Journal post, in full, as your voice/format reference "
            "(do not reuse its content, only its structure and tone):\n\n"
            f"TITLE: {example.get('title', '')}\n"
            f"EXCERPT: {example.get('excerpt', '')}\n"
            f"BODY:\n{example['body']}\n"
        )

    parts.append("Podcast episode transcript(s) to draw the post from:\n")
    for ep in episodes:
        parts.append(
            f"--- Episode: \"{ep['title']}\" (show: {ep['show']}) ---\n"
            f"{ep['transcript']}\n"
        )

    return "\n".join(parts)


def draft_post(episodes, existing_posts):
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 4096,
            "system": DRAFT_SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": build_user_prompt(episodes, existing_posts)}
            ],
        },
        timeout=300,
    )
    resp.raise_for_status()
    data = resp.json()
    text = data["content"][0]["text"].strip()

    # Model is instructed to return raw JSON; strip accidental code fences just in case.
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text)

    return json.loads(text)


# ---------------------------------------------------------------------------
# Assemble + write the .md draft
# ---------------------------------------------------------------------------
def assemble_frontmatter(fields, date, issue):
    lines = [
        "---",
        f"title: {fields['title']}",
        f"date: {date}",
        f"excerpt: {fields['excerpt']}",
        f'issue: "{issue}"',
        f"cta_text: {fields.get('cta_text', 'Start a Project')}",
    ]
    if fields.get("stats"):
        stats_str = "|".join(f"{s['number']}:{s['caption']}" for s in fields["stats"])
        lines.append(f"stats: {stats_str}")
    if fields.get("tags"):
        lines.append(f"tags: {fields['tags']}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def write_draft(fields, date, issue, source_episodes):
    slug = slugify(fields["title"])
    out_path = os.path.join(BANKED_DIR, f"{date}-{slug}.md")

    header_note = (
        f"<!-- Drafted automatically from podcast episode(s): "
        + "; ".join(f"\"{e['title']}\" ({e['link']})" for e in source_episodes)
        + " — review before moving to posts/. -->\n"
    )

    content = (
        assemble_frontmatter(fields, date, issue)
        + "\n"
        + fields["body_markdown"].strip()
        + "\n"
    )

    os.makedirs(BANKED_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header_note)
        f.write(content)

    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if not DEEPGRAM_API_KEY:
        print("Error: DEEPGRAM_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)
    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    config = load_config()
    state = load_state()

    new_episodes = find_new_episodes(config, state)
    if not new_episodes:
        print("No new episodes found. Nothing to draft.")
        return

    print(f"Found {len(new_episodes)} new episode(s). Transcribing...")
    for ep in new_episodes:
        print(f"  - Transcribing \"{ep['title']}\" ({ep['show']})")
        try:
            ep["transcript"] = transcribe_episode(ep["audio_url"])
        except Exception as exc:
            print(f"    Failed to transcribe: {exc}", file=sys.stderr)
            ep["transcript"] = None

    transcribed = [e for e in new_episodes if e.get("transcript")]
    if not transcribed:
        print("No episodes transcribed successfully. Nothing to draft.")
        return

    existing_posts = load_existing_posts()
    print("Drafting post with Claude...")
    fields = draft_post(transcribed, existing_posts)

    issue = next_issue_number(existing_posts)
    date = next_draft_date(existing_posts)
    out_path = write_draft(fields, date, issue, transcribed)
    print(f"Wrote draft: {out_path}")

    # Only mark episodes as processed once a draft was successfully produced.
    state["processed_episode_guids"].extend(e["guid"] for e in transcribed)
    save_state(state)
    print("Updated podcast_state.json")


if __name__ == "__main__":
    main()
