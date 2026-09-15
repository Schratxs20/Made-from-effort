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

## Podcast-to-post routine (draft only, needs setup before it's live)
`.github/workflows/podcast-to-post.yml` runs every Friday at 14:00 UTC (~10am
US Eastern), building the draft for the following week, plus on-demand via
"Run workflow". It checks the podcast feed(s) in `config/podcasts.json` for
episodes published in the last `lookback_days`, transcribes them with
Deepgram (with speaker labels), and asks Claude to surface 3-5 candidate
topics, pick the single strongest one, and draft a full Journal post in the
site's existing voice and frontmatter format. The draft is written to
`posts/banked/` — **not** `posts/`, and the workflow never touches or
triggers `build-journal.yml`. Nothing publishes until you read the draft and
move the file into `posts/` yourself.

Brand voice guardrails baked into the drafting prompt: documentary structure
(observation, then curiosity, then insight), the podcast is treated as
inspiration for original commentary — not a recap — any direct transcript
quote must be under 15 words and clearly attributed, and a fixed list of
cliches (grind, beast mode, hustle, crush it, dominate, hack, biohack,
"optimize everything", transformation, life-changing) is banned. If a draft
still slips one in, it gets flagged in an HTML comment at the top of the
draft file and in `podcast-log.md` rather than silently blocked.

Every run — whether or not it produces a draft — appends one line to
`podcast-log.md` at the repo root: episodes checked, any feed/episode
skipped and why (unreachable feed, no new episodes, transcription failure),
the topic chosen, and a link to the draft file. Transcripts themselves are
never written to disk or logged anywhere; they only exist in memory for the
run's duration.

Shows currently configured in `config/podcasts.json` — real RSS feed URLs,
resolved via Apple's podcast lookup API and confirmed live (fetched and
parsed cleanly, 0 errors, real episodes with audio enclosures):
- **Open Residency** (Mark Brazil) — `https://anchor.fm/s/ffafb5b8/podcast/rss`
- **Founders** (David Senra) — `https://feeds.megaphone.fm/DSLLC6297708582`
- **The Grant Owen Podcast** — `https://feed.podbean.com/grantowenpodcast/feed.xml`

None of the three are Spotify-exclusive — all three have a real public feed,
which is what makes this routine possible for them in the first place. If
you ever swap in a different show, the same lookup trick works for any show
listed on Apple Podcasts: open
`https://itunes.apple.com/lookup?id=<applePodcastsId>&entity=podcast` in a
browser (find the Apple Podcasts ID in the show's apple.com/podcast URL) and
read the `feedUrl` field from the JSON it returns.

Before enabling the schedule:
1. `config/podcasts.json` is already filled in with the three shows above —
   no edit needed unless you're changing the show list.
2. Add two repo secrets under Repo Settings > Secrets and variables > Actions:
   - `DEEPGRAM_API_KEY` — from https://deepgram.com
   - `ANTHROPIC_API_KEY` — from https://console.anthropic.com
3. `config/podcast_state.json` tracks which episode GUIDs have already been
   drafted, so the same episode is never turned into a second post. It's
   updated automatically by the workflow — don't hand-edit it unless you're
   deliberately resetting what counts as "already processed."

Local testing (optional):
```
pip install -r scripts/requirements-podcast.txt
DEEPGRAM_API_KEY=... ANTHROPIC_API_KEY=... python3 scripts/podcast_to_post.py
```
