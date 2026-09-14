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
`.github/workflows/podcast-to-post.yml` runs weekly (Mondays, and on-demand via
"Run workflow"). It checks the podcast feed(s) in `config/podcasts.json` for
new episodes, transcribes them with Deepgram, and asks Claude to pick the
strongest topic and draft a full Journal post in the site's existing voice
and frontmatter format. The draft is written to `posts/banked/` — **not**
`posts/`, so it never goes live automatically. Nothing publishes until you
read the draft and move the file into `posts/` yourself.

Before enabling the schedule:
1. Edit `config/podcasts.json` and replace the placeholder `name`/`rss_url`
   with your show's real public RSS feed URL (Spotify does not expose one —
   check your podcast host, e.g. Apple Podcasts, Libsyn, Transistor).
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
