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

## Podcast-to-Journal-post routine (no API keys, no audio transcription — reads existing free transcripts/notes)
This is a single **Claude Code Routine** ("Weekly Podcast Journal Draft
(Fri)") — a scheduled trigger, same mechanism as the existing "Twice-Weekly
Journal Drafts" and "Daily Program" Routines — that fires weekly (Fridays,
14:00 UTC) into a live session. It does not download or listen to any
audio, and does not run any transcription model. Instead, for each new
episode it finds, it looks for a **free, already-published transcript or
detailed notes page** for that specific episode and reads that.

Each firing:
1. Checks the podcast feed(s) in `config/podcasts.json` for episodes
   published in the last `lookback_days`, using Apify's web-fetch tool to
   pull the RSS XML (this session's own network access is restricted and
   can't reach these hosts directly — confirmed, not assumed; Apify's
   infrastructure isn't subject to that restriction). Skips episodes
   already recorded in `config/podcast_state.json`.
2. For each new episode, tries to find a real transcript/notes source for
   that specific episode: the episode's own link (some shows, like
   Founders, publish detailed timestamped notes on their own site), then a
   web search for "<episode title> <show> transcript" if that doesn't turn
   up anything substantial (aggregators like Tapesearch or Podscripts
   sometimes have it). If nothing substantial is found for any new
   episode that week, it stops — no forced post, no fabricated content.
3. If a usable source was found, reads it, picks the single strongest
   concrete idea a guest (or host) actually taught, and writes one
   **original** Journal post connecting it to mindset/consistency, fitness,
   or gym design — in the site's existing voice and frontmatter format.
   Hard rules: never quote or paraphrase the source's actual sentences at
   length (read it for the idea, write in Scott's own words), never
   reproduce or save the source text anywhere in this repo, never invent a
   specific client story or result that isn't real.
4. Saves the post to `posts/banked/<date>-<slug>.md`, updates
   `config/podcast_state.json` so the episode isn't re-checked, appends a
   line to `podcast-log.md` (episodes checked, skipped and why, topic
   chosen — never the source text itself), commits, and pushes. Still
   never reaches `posts/` or the live site on its own — that move is yours
   to make after reading it.

Coverage is real but uneven, honestly: **Founders** (established, 450+
episodes) reliably has detailed per-episode notes on its own site.
**Open Residency** and **The Grant Owen Podcast** are much newer/smaller
shows — a free transcript won't always exist for their latest episode, and
some weeks the routine will legitimately find nothing and stay quiet
rather than making something up.

Shows currently configured in `config/podcasts.json` — real RSS feed URLs,
confirmed live:
- **Open Residency** (Mark Brazil) — `https://anchor.fm/s/ffafb5b8/podcast/rss`
- **Founders** (David Senra) — `https://feeds.megaphone.fm/DSLLC6297708582`
- **The Grant Owen Podcast** — `https://feed.podbean.com/grantowenpodcast/feed.xml`

If you ever swap in a different show, resolve any Apple-Podcasts-listed
show's real feed URL by opening
`https://itunes.apple.com/lookup?id=<applePodcastsId>&entity=podcast` in a
browser (find the Apple Podcasts ID in the show's apple.com/podcast URL) and
reading the `feedUrl` field from the JSON it returns.

To change the schedule, source shows, or drafting instructions, edit the
Routine itself (`update_trigger` on its trigger id, or ask a Claude Code
session to do it) — there's no workflow file for this one; it all lives in
the Routine's own prompt.
