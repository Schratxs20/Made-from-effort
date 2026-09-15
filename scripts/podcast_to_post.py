#!/usr/bin/env python3
"""
Made From Effort — Podcast-to-draft routine (no API keys, no accounts).

Runs weekly (Fridays, prepping for the following week). For each configured
podcast RSS feed, finds episodes published since the last run, downloads
the audio, and transcribes it LOCALLY on the runner using faster-whisper
(an open-source model that downloads once from Hugging Face's public model
hub — no account, no API key, no per-minute cost).

There is no AI drafting step, deliberately: picking a topic and writing
copy in the site's voice needs an LLM, and an LLM cannot be called without
an API key. So this script stops short of that. What it produces instead,
per run:
  - transcripts/<date>-<slug>.txt — the full local transcript of each new
    episode, timestamped, for a human (or an interactive Claude Code
    session) to read and write from.
  - posts/banked/<date>-needs-draft-<slug>.md — a frontmatter skeleton
    (correct date/issue number, matching the site's format) with a TODO
    body pointing at the transcript(s). Never auto-published — it isn't
    even a real post until someone writes it.
  - podcast-log.md — one summary line per run either way.

Usage:
    python3 scripts/podcast_to_post.py

Requires:
    pip install -r scripts/requirements-podcast.txt

Environment (all optional):
    WHISPER_MODEL_SIZE  - defaults to "base" (tiny/base/small/medium/large-v3)
    WHISPER_COMPUTE_TYPE - defaults to "int8" (fast on CPU)
"""

import glob
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone

import feedparser
import requests
from faster_whisper import WhisperModel

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(REPO_ROOT, "config", "podcasts.json")
STATE_PATH = os.path.join(REPO_ROOT, "config", "podcast_state.json")
POSTS_DIR = os.path.join(REPO_ROOT, "posts")
BANKED_DIR = os.path.join(POSTS_DIR, "banked")
TRANSCRIPTS_DIR = os.path.join(REPO_ROOT, "transcripts")
LOG_PATH = os.path.join(REPO_ROOT, "podcast-log.md")

WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "base")
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")

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
# Local transcription (faster-whisper) — no API key, no account
# ---------------------------------------------------------------------------
_whisper_model = None


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        # Downloads the model from Hugging Face's public hub on first run
        # (anonymous, no token needed) and caches it for subsequent runs.
        _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, compute_type=WHISPER_COMPUTE_TYPE)
    return _whisper_model


def download_audio(audio_url):
    resp = requests.get(audio_url, stream=True, timeout=600)
    resp.raise_for_status()
    suffix = os.path.splitext(audio_url.split("?")[0])[1] or ".mp3"
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1 << 20):
            f.write(chunk)
    return path


def transcribe_episode(audio_url):
    audio_path = download_audio(audio_url)
    try:
        model = get_whisper_model()
        segments, _info = model.transcribe(audio_path, beam_size=5)
        lines = []
        for seg in segments:
            minutes, seconds = divmod(int(seg.start), 60)
            lines.append(f"[{minutes:02d}:{seconds:02d}] {seg.text.strip()}")
        return "\n".join(lines)
    finally:
        os.remove(audio_path)


# ---------------------------------------------------------------------------
# Existing posts — used only for issue numbering / date sequencing
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
        fm_block = m.group(1)
        meta = {}
        for line in fm_block.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip('"').strip("'")
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
# Write transcript file(s) + the TODO draft skeleton
# ---------------------------------------------------------------------------
def write_transcripts(episodes, date):
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    paths = []
    for ep in episodes:
        slug = slugify(f"{ep['show']}-{ep['title']}")
        path = os.path.join(TRANSCRIPTS_DIR, f"{date}-{slug}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"Show: {ep['show']}\n")
            f.write(f"Episode: {ep['title']}\n")
            f.write(f"Episode link: {ep['link']}\n")
            f.write("\n---\n\n")
            f.write(ep["transcript"])
            f.write("\n")
        paths.append(path)
    return paths


def write_stub_draft(episodes, transcript_paths, date, issue):
    # Title is a placeholder — there's no AI step to pick one. The slug is
    # derived from the first episode so the file has a stable, readable name.
    slug = slugify(f"needs-draft-{episodes[0]['show']}-{episodes[0]['title']}")
    out_path = os.path.join(BANKED_DIR, f"{date}-{slug}.md")

    episode_list = "\n".join(
        f"- \"{ep['title']}\" ({ep['show']}) — {ep['link']}" for ep in episodes
    )
    transcript_list = "\n".join(
        f"- {os.path.relpath(p, REPO_ROOT)}" for p in transcript_paths
    )

    body = f"""<!-- NEEDS DRAFT: no AI drafting step is configured for this routine (no API keys are used).
Pick the strongest angle from the episode(s) below, then write the post yourself — or paste a
transcript into an interactive Claude Code session and ask it to draft one, matching the format of
an existing posts/*.md file (numbered "## 01 / ..." sections, a pull-quote blockquote, a numbered
takeaway list, and a "## FAQ" section of **bolded question?** / answer pairs). Once written, fill in
the frontmatter above properly and move this file into posts/ to publish it. -->

TODO: draft this post.

Episode(s) this could be drawn from:
{episode_list}

Full transcript(s):
{transcript_list}
"""

    frontmatter = "\n".join([
        "---",
        "title: \"TODO — pick a title\"",
        f"date: {date}",
        "excerpt: \"TODO\"",
        f'issue: "{issue}"',
        "cta_text: Start a Project",
        "---",
        "",
    ])

    os.makedirs(BANKED_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(frontmatter)
        f.write(body)

    return out_path


# ---------------------------------------------------------------------------
# Weekly summary log (podcast-log.md) — never contains transcript text
# ---------------------------------------------------------------------------
def append_log(checked_count, skips, draft_path, transcript_paths):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    skipped_str = "; ".join(skips) if skips else "none"
    draft_str = os.path.relpath(draft_path, REPO_ROOT) if draft_path else "none"
    transcripts_str = ", ".join(os.path.relpath(p, REPO_ROOT) for p in transcript_paths) or "none"

    line = (
        f"- **{today}** — episodes checked: {checked_count}; "
        f"skipped: {skipped_str}; transcripts: {transcripts_str}; needs-draft file: {draft_str}\n"
    )

    is_new = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        if is_new:
            f.write("# Podcast-to-post run log\n\n")
            f.write("One line per run. No AI drafting happens automatically — see README.\n\n")
        f.write(line)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    config = load_config()
    state = load_state()

    new_episodes, skips = find_new_episodes(config, state)
    if not new_episodes:
        print("No new episodes found. Nothing to transcribe.")
        append_log(0, skips, None, [])
        return

    print(f"Found {len(new_episodes)} new episode(s). Transcribing locally (this can take a while)...")
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
        print("No episodes transcribed successfully. Nothing to write.")
        append_log(len(new_episodes), skips, None, [])
        return

    existing_posts = load_existing_posts()
    issue = next_issue_number(existing_posts)
    date = next_draft_date(existing_posts)

    transcript_paths = write_transcripts(transcribed, date)
    print(f"Wrote {len(transcript_paths)} transcript(s) to {TRANSCRIPTS_DIR}/")

    out_path = write_stub_draft(transcribed, transcript_paths, date, issue)
    print(f"Wrote needs-draft stub: {out_path}")

    # Only mark episodes as processed once transcripts were successfully produced.
    state["processed_episode_guids"].extend(e["guid"] for e in transcribed)
    save_state(state)
    print("Updated podcast_state.json")

    append_log(len(new_episodes), skips, out_path, transcript_paths)


if __name__ == "__main__":
    main()
