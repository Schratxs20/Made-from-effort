#!/usr/bin/env python3
"""
Made From Effort — Podcast transcript fetcher (no API keys, no accounts).

Meant to be run by the "Weekly Podcast Journal Draft" Claude Code Routine,
not by a GitHub Action. For each configured podcast RSS feed, finds
episodes published since the last run, downloads the audio, and
transcribes it LOCALLY using faster-whisper (an open-source model that
downloads once from Hugging Face's public model hub — no account, no API
key, no per-minute cost).

This script's job stops at producing transcripts. The Routine that invokes
it is the one that reads the resulting transcript(s), decides what's worth
writing about, and drafts the actual Journal post — because that step
needs an LLM, and the live Claude Code session firing this Routine already
is one, with no separate key to manage.

Output per run:
  - transcripts/<date>-<slug>.txt — the full local transcript of each new
    episode, timestamped.
  - podcast-log.md — one summary line per run either way.
  - Prints the transcript paths it wrote to stdout so the calling agent
    knows what to read next.

Usage:
    python3 scripts/podcast_to_post.py

Requires:
    pip install -r scripts/requirements-podcast.txt

Environment (all optional):
    WHISPER_MODEL_SIZE   - defaults to "base" (tiny/base/small/medium/large-v3)
    WHISPER_COMPUTE_TYPE - defaults to "int8" (fast on CPU)
"""

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


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


# ---------------------------------------------------------------------------
# Write transcript file(s)
# ---------------------------------------------------------------------------
def write_transcripts(episodes):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    paths = []
    for ep in episodes:
        slug = slugify(f"{ep['show']}-{ep['title']}")
        path = os.path.join(TRANSCRIPTS_DIR, f"{today}-{slug}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"Show: {ep['show']}\n")
            f.write(f"Episode: {ep['title']}\n")
            f.write(f"Episode link: {ep['link']}\n")
            f.write("\n---\n\n")
            f.write(ep["transcript"])
            f.write("\n")
        paths.append(path)
    return paths


# ---------------------------------------------------------------------------
# Weekly summary log (podcast-log.md) — never contains transcript text
# ---------------------------------------------------------------------------
def append_log(checked_count, skips, transcript_paths):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    skipped_str = "; ".join(skips) if skips else "none"
    transcripts_str = ", ".join(os.path.relpath(p, REPO_ROOT) for p in transcript_paths) or "none"

    line = (
        f"- **{today}** — episodes checked: {checked_count}; "
        f"skipped: {skipped_str}; transcripts: {transcripts_str}\n"
    )

    is_new = not os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        if is_new:
            f.write("# Podcast-to-post run log\n\n")
            f.write(
                "One line per run. Drafting happens separately, in the Routine's own "
                "live session — see README.\n\n"
            )
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
        append_log(0, skips, [])
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
        print("No episodes transcribed successfully.")
        append_log(len(new_episodes), skips, [])
        return

    transcript_paths = write_transcripts(transcribed)
    print(f"Wrote {len(transcript_paths)} transcript(s):")
    for p in transcript_paths:
        print(f"  - {os.path.relpath(p, REPO_ROOT)}")

    # Only mark episodes as processed once transcripts were successfully produced.
    state["processed_episode_guids"].extend(e["guid"] for e in transcribed)
    save_state(state)
    print("Updated podcast_state.json")

    append_log(len(new_episodes), skips, transcript_paths)


if __name__ == "__main__":
    main()
