# Four-part page publishing routine

Scott requested this routine on October 28, 2026, based on Lawrence Hitches's
UNHINGED checklist at https://www.lawrencehitches.com/watch/unhinged/#checklist.
It applies to all indexable public pages, including future Journal and static
pages. Drafts, banked posts, gated guides, email exports, redirects, and error
pages are deliberately outside the public-content inventory.

## 1. Faithful Markdown for every public page

Install `requirements-build.txt`, then run `python scripts/build_journal.py`
when publishing an article or changing the sitemap. After static-page edits,
run `python scripts/build_ai_assets.py` directly. A new static page must also
be added to `STATIC_PAGES` in the Journal builder. CI rejects omitted pages.

The generator copies the page title, original headings, paragraphs, lists,
tables, and links. It strips navigation, scripts, forms, dialogs, buttons,
and footers. It does not rewrite or summarize. Each HTML page advertises its
alternative using `rel=alternate`; `/llms.txt` links every Markdown copy.
`/ai-pages/manifest.json` inventories source path, current title, text digest,
and the per-page monitoring/test status. Copies live under `/ai-pages/` and
are excluded from search indexing as duplicate representations, not blocked
from crawler access. Requests to the original URL that explicitly prefer
`Accept: text/markdown` receive the same generated content. Ordinary HTML and
Googlebot receive the normal site unless they request another format.
No user-agent cloaking or separate sales claims are used.

Cloudflare build command: `pip install -r requirements-build.txt && python
scripts/build_ai_assets.py`. This ensures new pages get copies during the
deployment itself. The GitHub Journal workflow persists generated files too.
After deployment check every sitemap URL and its Markdown endpoint, including
HTML/Markdown content negotiation, status, correct type, and canonical source.

## 2. Weekly AI crawler review

The existing Friday 9 AM America/New_York search review also reviews the
last complete seven days in Cloudflare AI Crawl Control. Track the top ten
public paths by successful AI fetches and crawler, plus important pages with
no observed fetch. Join against the current live sitemap/manifest, not an
old hard-coded page list. Keep canonical paths and legacy redirect requests
separate. Distinguish search crawlers, training crawlers, and user-triggered
assistant fetches; unknown/spoofable user agents are not verified bots.

Record window, time zone, account/domain, reporting limits/sampling, source,
successful versus blocked/error requests, and missing evidence. Only say
zero when the available report covers the whole relevant window/path set.
Missing access is unknown, not zero. Investigate live content, internal links,
robots, and HTTP responses before changing copy. AI fetches are not citations,
rankings, human visits, or leads. Do not buy a plan or widen a token silently.

## 3. Title tests, one controlled page at a time

Every page has an inventory record and enters an eligibility review. Keep the
original title until a suitable baseline exists. Start with high-intent service
pages, then projects/articles; utility/privacy/facts pages are low priority.
The local private title ledger records current title, target query, candidate
variants, baseline window/filters, sample adequacy, deployment and recrawl dates,
changed title, comparison window, result, and keep/revert decision.

October 28 baseline: the 28-day site report through October 26 showed 24
impressions and zero clicks. No page has enough evidence to judge a title lift.
Do not start a test just to mark this step complete. For the next review, use
at least a full 28-day baseline and assess adequacy for the current CTR and
smallest worthwhile lift. A practical screening floor is 200 page impressions
and 10 clicks, but that floor is not proof of statistical power. Require
reasonably stable query/device/country/rank distribution, enough observations
for a defensible interval, and no overlapping redesign or major content change.

Write three accurate variants (aim under 60 characters, a drafting preference
rather than a Google limit), keeping the main query and changing only the
promise, audience, or specificity. Record why each might help. Change only the
HTML title for the selected experiment; leave body, metadata, and other pages
alone. Confirm Google has recrawled before starting an equal-length 28-day
comparison window with the same filters. Track clicks, impressions, CTR,
average position, query mix, and qualified inquiries when attributable. If
sample size or confounding prevents a conclusion, extend or mark inconclusive;
do not claim causality from raw percentages. Revert a verified material loss.

## 4. One sourced business facts page, linked throughout

`config/business-facts.json` is the editorial source for `/llm-info` and
`/api/facts.json`. Each fact has one short supported statement, a public source,
a checked date, and an evidence excerpt checked against that source during
builds. Footer links on all public pages make the facts discoverable. The
facts page is readable by people as well as AI tools. It does not publish
Scott's private home address, imply certification that has not been verified,
invent business start dates/prices/awards, or turn planned projects into
completed work. The coaching-start date is not a business incorporation date.
Changes require source review; never advance checked dates automatically.

## Validation and evidence boundaries

Run `python -m unittest discover -s tests` and `node --test tests/*.test.mjs`.
`python scripts/build_ai_assets.py --check` detects stale copies. Preserve
existing inquiry routes, approved photos, and original content. Verify desktop
and narrow mobile navigation to the facts page and its source links.

This is an accessibility/discovery and measurement routine. Google explicitly
says special AI files and Markdown are not requirements for its AI search
features, and it does not use them as special ranking signals. Completion of
this checklist is not evidence of increased rankings, citations, or inquiries.

Primary references, checked October 28, 2026:

- https://developers.google.com/search/docs/fundamentals/ai-optimization-guide
- https://developers.google.com/search/docs/appearance/title-link
- https://developers.cloudflare.com/fundamentals/reference/markdown-for-agents/
- https://developers.cloudflare.com/ai-crawl-control/features/analyze-ai-traffic/
- https://developers.cloudflare.com/ai-crawl-control/reference/graphql-api/
