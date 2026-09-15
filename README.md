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

## Podcast-to-transcript routine (no API keys, no accounts — needs a manual writing step)
`.github/workflows/podcast-to-post.yml` runs every Friday at 14:00 UTC (~10am
US Eastern), plus on-demand via "Run workflow". It checks the podcast
feed(s) in `config/podcasts.json` for episodes published in the last
`lookback_days`, downloads the audio, and transcribes it **locally on the
GitHub Actions runner** using [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
— an open-source speech-to-text model. No Deepgram, no Anthropic API, no
signup anywhere. The model itself downloads once, anonymously, from Hugging
Face's public model hub (no token needed) and is cached for later runs.

**This intentionally does not write the blog post for you.** Picking the
strongest topic and drafting copy in the site's voice needs an LLM, and an
LLM cannot be called without an API key — which is exactly what was ruled
out. So each run instead produces:
- `transcripts/<date>-<slug>.txt` — the full local transcript of each new
  episode, timestamped.
- `posts/banked/<date>-needs-draft-<slug>.md` — a frontmatter skeleton with
  the correct date and issue number already filled in, a `TODO` body, and
  links to the transcript(s) it could be drawn from. It is **not** a real
  post — nothing here ever reaches `posts/` or the live site on its own.
- `podcast-log.md` at the repo root — one summary line per run either way
  (episodes checked, anything skipped and why, which files were written).

To actually turn a transcript into a post: open the `needs-draft` file,
read the linked transcript(s), and either write the post yourself following
the format of an existing `posts/*.md` file, or start an interactive Claude
Code session, paste in (or point it at) the transcript, and ask it to draft
one. Once it reads like the rest of the Journal, fill in the real
title/excerpt/tags and move the file from `posts/banked/` into `posts/` —
that's what actually publishes it, same as any other post.

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

Before enabling the schedule:
1. Nothing to sign up for — `config/podcasts.json` is already filled in
   with the three shows above.
2. `config/podcast_state.json` tracks which episode GUIDs have already been
   transcribed, so the same episode is never processed twice. It's updated
   automatically by the workflow — don't hand-edit it unless you're
   deliberately resetting what counts as "already processed."
3. Transcription runs on the Action's own (free) CPU runner, so it's slower
   than a paid API — a ~1 hour episode can take a while on `WHISPER_MODEL_SIZE=base`
   (the default). If runs are timing out or eating too many Action minutes,
   either set `WHISPER_MODEL_SIZE=tiny` (faster, lower quality) as a repo
   variable/env in the workflow, or lower `max_episodes_per_run` in
   `config/podcasts.json`.

Local testing (optional):
```
pip install -r scripts/requirements-podcast.txt
python3 scripts/podcast_to_post.py
```
