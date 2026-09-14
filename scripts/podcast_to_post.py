#!/usr/bin/env python3
"""
Made From Effort — Podcast-to-post drafting routine.

Runs weekly (Fridays, building the post for the following week). For each
configured podcast RSS feed, finds episodes published since the last run,
transcribes them (Deepgram, with speaker labels), and hands the transcripts
to Claude to surface a handful of candidate topics, pick the single
strongest one, and draft a full Journal post in the site's existing voice
and frontmatter format.

The draft is written to posts/banked/ — NOT posts/ — so it never goes live
on its own and never touches the existing build-journal workflow. A human
has to read it and move it into posts/ before it publishes. A one-line
summary (episodes checked, episodes skipped and why, topic chosen, draft
link) is appended to podcast-log.md at the repo root on every run, whether
or not a draft was produced. Transcripts themselves are never written to
disk or logged anywhere — they exist only in memory for the duration of
the run.

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
LOG_PATH = os.path.join(REPO_ROOT, "podcast-log.md")

DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

PLACEHOLDER_MARKERS = ("REPLACE_WITH_", "REPLACE-WITH-")

# Cliches the brand voice avoids. Checked against the drafted title/excerpt/
# body after generation; any hit gets flagged in podcast-log.md for review
# rather than silently blocking the draft (the model can slip, review can't).
BANNED_PHRASES = [
    "grind", "beast mode", "hustle", "crush it", "dominate", "hack",
    "biohack", "optimize everything", "transformation", "life-changing",
]


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
    """Returns (candidates, skips). A feed that's unreachable, unconfigured,
    or has no new episodes is never fatal — it's recorded in `skips` with a
    reason and the run continues with whatever other feeds turned up."""
    lookback_days = config.get("lookback_days", 10)
    max_episodes = config.get("max_episodes_per_run", 5)
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    seen = set(state.get("processed_episode_guids", []))

    candidates = []
    skips = []
    for feed_cfg in config.get("feeds", []):
        name = feed_cfg.get("name", "Unknown show")
        rss_url = feed_cfg.get("rss_url", "")

        if is_placeholder(rss_url) or is_placeholder(name):
            skips.append(f"{name}: RSS feed not configured yet")
            continue

        try:
            parsed = feedparser.parse(rss_url)
        except Exception as exc:
            skips.append(f"{name}: feed fetch failed ({exc})")
            continue

        if parsed.bozo and not parsed.entries:
            skips.append(f"{name}: feed unreachable or unparseable ({parsed.bozo_exception})")
            continue

        found_new = 0
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
                continue

            candidates.append({
                "show": name,
                "guid": guid,
                "title": entry.get("title", "Untitled episode"),
                "published": published_dt,
                "audio_url": audio_url,
                "link": entry.get("link", ""),
            })
            found_new += 1

        if found_new == 0:
            skips.append(f"{name}: no new episodes in the last {lookback_days} days")

    candidates.sort(key=lambda e: e["published"] or datetime.min.replace(tzinfo=timezone.utc))
    return candidates[:max_episodes], skips


# ---------------------------------------------------------------------------
# Transcription (Deepgram) — with speaker labels + timestamps
# ---------------------------------------------------------------------------
def transcribe_episode(audio_url):
    resp = requests.post(
        "https://api.deepgram.com/v1/listen",
        params={
            "model": "nova-2",
            "smart_format": "true",
            "punctuate": "true",
            "diarize": "true",
            "utterances": "true",
        },
        headers={
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "application/json",
        },
        json={"url": audio_url},
        timeout=600,
    )
    resp.raise_for_status()
    data = resp.json()

    utterances = data["results"].get("utterances")
    if not utterances:
        return data["results"]["channels"][0]["alternatives"][0]["transcript"]

    lines = []
    for u in utterances:
        minutes, seconds = divmod(int(u.get("start", 0)), 60)
        lines.append(f"[{minutes:02d}:{seconds:02d}] Speaker {u.get('speaker', 0)}: {u['transcript']}")

    transcript = "\n".join(lines)
    # Guard against extreme-length episodes blowing up the drafting prompt.
    max_chars = 60000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n[...transcript truncated for length...]"
    return transcript


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
madefromeffort.com, run by Scott Schratwieser (Performance Edge Training + Gym Design, Long Island, NY).

BRAND VOICE
Write in Scott's voice: plain language, documentary structure (an observation, then curiosity about why
it happens, then the insight that resolves it), told through one concrete story per post. Short punchy
sentences mixed with longer ones. Brand pillars to draw on, don't just name them: wellness architecture,
"the spaces we build shape the habits we keep," craftsmanship, quiet confidence, longevity, discipline, and
how environment shapes outcomes.

Never use these words/phrases: grind, beast mode, hustle, crush it, dominate, hack, biohack, optimize
everything, transformation, life-changing. Use "elite" and "luxury" sparingly, only when they're earned by a
specific detail, never as a generic descriptor.

Treat the podcast transcript(s) as inspiration for ORIGINAL commentary in Scott's voice, not something to
recap or summarize. You may include a direct quote from a transcript only if it is under 15 words and clearly
attributed to the speaker by name or role (e.g. "as the show's host put it, '...'"). Everything else in the
post must be Scott's own framing and ideas — never invent facts, figures, or client details that are not
actually present in the transcript(s) you were given.

YOUR JOB
1. Read the transcript(s). Identify 3 to 5 candidate topics/angles that connect a specific moment or idea in
   the transcript(s) to the Journal's beat (training, gym design/build, discipline and systems, environment
   shaping behavior). Each candidate should be concrete, not a generic theme.
2. Pick the single strongest candidate — the one with the most specific, well-supported story to tell — and
   draft one full Journal post about it. Do not try to cover every candidate; one sharp angle beats a broad
   summary.

Output ONLY a single JSON object (no markdown fences, no commentary) with these fields:
- "candidate_topics": array of 3-5 short strings, the candidate angles you considered.
- "chosen_topic": string, a short phrase naming the one you picked and why it won (one sentence).
- "title": string, a direct question or bold claim, matching the tone of existing titles.
- "excerpt": string, 1-2 sentences, the RSS/email preview text.
- "cta_text": string, either "Start a Project" or "Train With Me" (pick whichever fits the post's theme).
- "tags": string, 3-5 comma-separated topical tags.
- "stats": array of 0-4 objects {"number": string, "caption": string} — ONLY include real figures actually \
stated in the transcript (a length, a dollar figure, a count, a duration). If no solid numbers exist in the \
source material, return an empty array. Never invent a number.
- "body_markdown": string, the full post body in Markdown, following this exact shape (this matches the
  site's existing posts and its build script parses it with a strict regex, so the shape below is required):
    - Opens with 1-3 short paragraphs setting up the hook (often a direct-answer style first line) —
      this is the "observation."
    - Then numbered "## 01 / <Section Title>" headers (typically 3 sections following the documentary arc:
      the observation/mistake, the curiosity/why it gets missed, the insight/fix — adapt titles to the story).
    - At least one "> pull quote" blockquote — a single punchy sentence in Scott's own voice, not a direct
      transcript quote unless it meets the 15-word/attribution rule above.
    - A numbered practical takeaway list ("What this means if you're planning ...:") of 3-5 items, each
      starting with a **bolded lead-in phrase**.
    - A short closing (1-2 paragraphs) that lands the "whole game" point.
    - Ends with a "## FAQ" section: 3-4 question/answer pairs, each question as its own **bolded line ending
      in a question mark**, followed immediately by a plain paragraph answer.

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

    parts.append("Podcast episode transcript(s) to draw the post from (speaker-labeled, timestamped):\n")
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


def find_banned_phrases(fields):
    haystack = " ".join([
        fields.get("title", ""),
        fields.get("excerpt", ""),
        fields.get("body_markdown", ""),
    ]).lower()
    return [p for p in BANNED_PHRASES if p in haystack]


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


def write_draft(fields, date, issue, source_episodes, banned_hits):
    slug = slugify(fields["title"])
    out_path = os.path.join(BANKED_DIR, f"{date}-{slug}.md")

    notes = [
        "Drafted automatically from podcast episode(s): "
        + "; ".join(f"\"{e['title']}\" ({e['link']})" for e in source_episodes)
        + " — review before moving to posts/.",
        f"Chosen topic: {fields.get('chosen_topic', 'n/a')}",
    ]
    if banned_hits:
        notes.append(f"FLAGGED: possible off-voice phrase(s) found: {', '.join(banned_hits)} — check before publishing.")

    header_note = "".join(f"<!-- {n} -->\n" for n in notes)

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
# Weekly summary log (podcast-log.md) — never contains transcript text
# ---------------------------------------------------------------------------
def append_log(checked_count, skips, topic, draft_path):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    skipped_str = "; ".join(skips) if skips else "none"
    draft_str = os.path.relpath(draft_path, REPO_ROOT) if draft_path else "none"

    line = (
        f"- **{today}** — episodes checked: {checked_count}; "
        f"skipped: {skipped_str}; topic chosen: {topic or 'none'}; draft: {draft_str}\n"
    )

    is_new = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        if is_new:
            f.write("# Podcast-to-post run log\n\n")
            f.write(
                "One line per run. Transcripts are never stored here or anywhere else — "
                "this is a summary only.\n\n"
            )
        f.write(line)


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

    new_episodes, skips = find_new_episodes(config, state)
    if not new_episodes:
        print("No new episodes found. Nothing to draft.")
        append_log(0, skips, None, None)
        return

    print(f"Found {len(new_episodes)} new episode(s). Transcribing...")
    for ep in new_episodes:
        print(f"  - Transcribing \"{ep['title']}\" ({ep['show']})")
        try:
            ep["transcript"] = transcribe_episode(ep["audio_url"])
        except Exception as exc:
            print(f"    Failed to transcribe: {exc}", file=sys.stderr)
            ep["transcript"] = None
            skips.append(f"{ep['show']} — \"{ep['title']}\": transcription failed ({exc})")

    transcribed = [e for e in new_episodes if e.get("transcript")]
    if not transcribed:
        print("No episodes transcribed successfully. Nothing to draft.")
        append_log(len(new_episodes), skips, None, None)
        return

    existing_posts = load_existing_posts()
    print("Drafting post with Claude...")
    fields = draft_post(transcribed, existing_posts)

    banned_hits = find_banned_phrases(fields)
    if banned_hits:
        print(f"Warning: draft contains flagged phrase(s): {', '.join(banned_hits)}")

    issue = next_issue_number(existing_posts)
    date = next_draft_date(existing_posts)
    out_path = write_draft(fields, date, issue, transcribed, banned_hits)
    print(f"Wrote draft: {out_path}")

    # Only mark episodes as processed once a draft was successfully produced.
    state["processed_episode_guids"].extend(e["guid"] for e in transcribed)
    save_state(state)
    print("Updated podcast_state.json")

    append_log(len(new_episodes), skips, fields.get("chosen_topic"), out_path)


if __name__ == "__main__":
    main()
