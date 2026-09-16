# Journal build system — Made From Effort

## What this is
A lightweight static blog system for madefromeffort.com. Write posts in Markdown,
push to GitHub, and everything else (HTML pages, index listing, RSS feed) builds
automatically.

## Folder structure to drop into your repo root
```
posts/                          <- write new posts here as .md files
scripts/build_journal.py        <- the build script
.github/workflows/build-journal.yml   <- runs the build automatically on push
journal/                        <- generated output (created automatically, don't hand-edit)
```

## Writing a new post
1. Copy `posts/2026-07-08-plan-you-follow.md` as a template.
2. Name the new file `YYYY-MM-DD-your-slug.md`.
3. Fill in the frontmatter (between the `---` lines):
   - `title` (required)
   - `date` (required, format YYYY-MM-DD)
   - `excerpt` (shows in the RSS feed / index list / email preview text)
   - `issue` (optional — the "NO. 0XX" tag)
   - `image` (optional — path to a hero image, e.g. /assets/journal/hero-015.jpg)
4. Write the body in Markdown below the frontmatter. Use:
   - `## Heading` for section headers
   - `> quote` for pull-quotes
   - `**bold**` / `*italic*` as normal
   - `![alt](url)` for inline images
5. Commit and push to `main`. GitHub Actions builds the HTML + feed.xml automatically
   and commits it back to the repo within ~30 seconds.

## Local testing (optional, before pushing)
```
pip install markdown
python3 scripts/build_journal.py
```
Then open journal/index.html or journal/your-post.html in a browser to preview.

## Connecting to Beehiiv
Once this is live at https://www.madefromeffort.com/journal/feed.xml, add that URL
as an RSS source in Beehiiv's automation settings so each new post auto-sends as
an email.

## One-time setup notes
- Make sure GitHub Pages is serving from the branch this workflow pushes to (main).
- The workflow needs "Read and write permissions" enabled under
  Repo Settings > Actions > General > Workflow permissions.

## Podcast-to-Journal-post routine (no API keys — a GitHub Action + a Claude Code Routine, two stages)
This is two pieces working together, not one. It used to be a single Claude
Code Routine doing everything, but that Routine's session runs inside a
network-restricted container that cannot reach podcast RSS/audio hosts at
all (confirmed directly: 403s at the TCP CONNECT level on the feed hosts
*and* the audio CDNs, not a rate limit or flakiness). Splitting fetch from
drafting fixes that cleanly, and both stages still need zero API keys.

**Stage 1 — `.github/workflows/podcast-to-post.yml`** (GitHub Action, runs
Fridays at 12:00 UTC). GitHub-hosted runners have normal unrestricted
internet access, so this is the only place that talks to podcast feeds and
audio CDNs directly:
1. Checks the podcast feed(s) in `config/podcasts.json` for episodes
   published in the last `lookback_days`.
2. Downloads the audio for any new episode and transcribes it **locally**
   with [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
   (open-source, downloads its model anonymously from Hugging Face's
   public hub — no account, no key, no cost).
3. Writes `transcripts/<date>-<slug>.txt` per new episode, appends a line
   to `podcast-log.md`, updates `config/podcast_state.json` (tracks which
   episode GUIDs are already transcribed so nothing repeats), and pushes.

**Stage 2 — "Weekly Podcast Journal Draft (Fri)"** (Claude Code Routine,
fires 2 hours later at 14:00 UTC into a live session — same mechanism as
the existing "Twice-Weekly Journal Drafts" and "Daily Program" Routines).
It never fetches or transcribes anything itself:
1. Pulls the latest repo state (picking up whatever Stage 1 just committed).
2. Reads any transcript(s) sitting in `transcripts/*.txt` that haven't been
   drafted yet (anything already moved into `transcripts/drafted/` is done).
3. Picks the single strongest concrete idea a guest taught, and writes one
   **original** Journal post connecting it to mindset/consistency, fitness,
   or gym design — in the site's existing voice and frontmatter format. It
   never quotes or paraphrases the transcript's actual sentences, and never
   invents a specific client story or result that isn't real (same rule
   the Gmail-based Routine follows).
4. Saves the post to `posts/banked/<date>-<slug>.md`, moves the transcript(s)
   it used into `transcripts/drafted/`, commits, and pushes. It still never
   reaches `posts/` or the live site on its own — that move is yours to
   make after reading it.

Shows currently configured in `config/podcasts.json` — real RSS feed URLs,
confirmed live (fetched and parsed cleanly, real episodes with audio
enclosures):
- **Open Residency** (Mark Brazil) — `https://anchor.fm/s/ffafb5b8/podcast/rss`
- **Founders** (David Senra) — `https://feeds.megaphone.fm/DSLLC6297708582`
- **The Grant Owen Podcast** — `https://feed.podbean.com/grantowenpodcast/feed.xml`

None of the three are Spotify-exclusive — all three have a real public feed,
which is what makes this routine possible for them in the first place. If
you ever swap in a different show, resolve any Apple-Podcasts-listed show's
real feed URL by opening
`https://itunes.apple.com/lookup?id=<applePodcastsId>&entity=podcast` in a
browser (find the Apple Podcasts ID in the show's apple.com/podcast URL) and
reading the `feedUrl` field from the JSON it returns.

Notes:
- Transcription runs on the Action's own (free) CPU runner, so it's slower
  than a paid API on a long episode. `WHISPER_MODEL_SIZE` (default `base`)
  can be set to `tiny` for speed over accuracy if that's ever an issue, or
  lower `max_episodes_per_run` in `config/podcasts.json`.
- To change Stage 1's schedule or source shows, edit
  `.github/workflows/podcast-to-post.yml` / `config/podcasts.json` like any
  other file in this repo. To change Stage 2's schedule or drafting
  instructions, edit the Routine itself (`update_trigger` on its trigger
  id, or ask a Claude Code session to do it) — there's no workflow file
  for that half.

Local testing of just the fetch/transcribe step (optional — needs real
internet access, so this won't work from inside a network-restricted
Claude Code session, only from a normal machine or CI runner):
```
pip install -r scripts/requirements-podcast.txt
python3 scripts/podcast_to_post.py
```
