#!/usr/bin/env python3
"""
Made From Effort — Journal build script.

Reads Markdown posts from /posts, renders them into styled HTML pages in
/journal, builds a /journal/index.html listing page, and generates a valid
RSS 2.0 feed at /journal/feed.xml (used by Beehiiv's RSS-to-email automation).

Usage:
    python3 scripts/build_journal.py

Requires:
    pip install markdown
"""

import os
import re
import glob
import html
import markdown
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config — edit these to match your site
# ---------------------------------------------------------------------------
SITE_URL = "https://www.madefromeffort.com"
SITE_TITLE = "Made From Effort"
SITE_DESCRIPTION = "Training, gym design, and systems that actually hold up."
POSTS_DIR = "posts"
OUTPUT_DIR = "journal"
ASSETS_DIR = "assets"

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Tiny frontmatter parser (avoids needing python-frontmatter as a dependency)
# ---------------------------------------------------------------------------
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

def parse_post(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    m = FRONTMATTER_RE.match(raw)
    if not m:
        raise ValueError(f"{path}: missing --- frontmatter block")

    fm_block, body_md = m.group(1), m.group(2)

    meta = {}
    for line in fm_block.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip('"').strip("'")
        meta[key.strip()] = value

    required = ["title", "date"]
    for r in required:
        if r not in meta:
            raise ValueError(f"{path}: missing required frontmatter field '{r}'")

    slug = meta.get("slug") or slugify(meta["title"])
    meta["slug"] = slug
    meta["body_html"] = markdown.markdown(
        body_md.strip(), extensions=["extra", "sane_lists"]
    )
    meta["source_path"] = path
    return meta


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


# ---------------------------------------------------------------------------
# Templates — matches the Made From Effort design system
# ---------------------------------------------------------------------------
STYLE_BLOCK = """
  @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,500&family=Inter:wght@400;500;600&display=swap');
  * { box-sizing: border-box; }
  body { margin:0; padding:0; background:#EAE7DE; font-family:'Inter',-apple-system,sans-serif; }
  .wrap { max-width:700px; margin:0 auto; background:#F7F5F0; border-left:1px solid #1C1C1A; border-right:1px solid #1C1C1A; min-height:100vh; }
  .masthead { padding:28px 32px 20px; border-bottom:1px solid #1C1C1A; display:flex; align-items:center; justify-content:space-between; }
  .masthead a { text-decoration:none; }
  .wordmark { font-family:'Bebas Neue',sans-serif; font-size:22px; letter-spacing:2px; color:#1C1C1A; }
  .bib { font-family:'Bebas Neue',sans-serif; font-size:12px; letter-spacing:3px; color:#3F4A3C; border:1px solid #3F4A3C; padding:4px 10px; }
  .photo { width:100%; display:block; }
  .eyebrow { padding:26px 32px 0; font-family:'Bebas Neue',sans-serif; font-size:13px; letter-spacing:4px; color:#8B4A3B; }
  .headline { padding:10px 32px 24px; font-family:'Fraunces',serif; font-weight:600; font-size:32px; line-height:1.1; color:#1C1C1A; border-bottom:1px solid #D8D4C9; margin-bottom:28px; }
  .body-copy { padding:0 32px; font-family:'Inter',sans-serif; font-size:16px; line-height:1.7; color:#2A2A26; }
  .body-copy p { margin:0 0 20px; }
  .body-copy h2 { font-family:'Fraunces',serif; font-weight:600; font-size:24px; color:#1C1C1A; margin:32px 0 14px; }
  .body-copy blockquote { font-family:'Fraunces',serif; font-style:italic; font-weight:500; font-size:21px; line-height:1.4; color:#1C1C1A; padding:4px 0 4px 20px; border-left:3px solid #3F4A3C; margin:8px 0 28px; }
  .body-copy img { width:100%; display:block; margin:0 0 28px; }
  .body-copy ol, .body-copy ul { padding-left: 20px; }
  .body-copy li { margin-bottom: 10px; }
  .meta-row { padding:0 32px 20px; font-family:'Bebas Neue',sans-serif; font-size:12px; letter-spacing:2px; color:#6B6B63; }
  .footer { background:#1C1C1A; padding:22px 32px; margin-top:20px; }
  .footer-links { display:flex; justify-content:center; gap:28px; padding-bottom:16px; border-bottom:1px solid #3A3A36; margin-bottom:14px; }
  .footer-links a { font-family:'Bebas Neue',sans-serif; font-size:13px; letter-spacing:2px; color:#F7F5F0; text-decoration:none; }
  .footer-fine { text-align:center; font-family:'Inter',sans-serif; font-size:11px; line-height:1.6; color:#8A8A82; }
  .footer-fine a { color:#8A8A82; text-decoration:underline; }
  /* index list */
  .post-list { padding:0 32px 32px; }
  .post-item { display:block; padding:22px 0; border-top:1px solid #D8D4C9; text-decoration:none; }
  .post-item:first-child { border-top:none; }
  .post-item-date { font-family:'Bebas Neue',sans-serif; font-size:12px; letter-spacing:2px; color:#8B4A3B; }
  .post-item-title { font-family:'Fraunces',serif; font-weight:600; font-size:22px; color:#1C1C1A; margin:6px 0; }
  .post-item-excerpt { font-family:'Inter',sans-serif; font-size:14px; color:#4A4A44; line-height:1.5; }
"""

FOOTER_HTML = """
    <div class="footer">
      <div class="footer-links">
        <a href="{site_url}/training.html">PERFORMANCE EDGE TRAINING</a>
        <a href="{site_url}/">HYBRID ENGINE</a>
      </div>
      <div class="footer-fine">
        Scott Schratwieser &middot; Massapequa, New York<br>
        <a href="{site_url}">{site_url_display}</a>
      </div>
    </div>
"""

def render_post_page(post):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(post['title'])} — {SITE_TITLE}</title>
<meta name="description" content="{html.escape(post.get('excerpt',''))}">
<style>{STYLE_BLOCK}</style>
</head>
<body>
  <div class="wrap">
    <div class="masthead">
      <a href="{SITE_URL}/journal/"><span class="wordmark">MADE FROM EFFORT</span></a>
      <span class="bib">NO. {html.escape(post.get('issue', '—'))}</span>
    </div>
    {'<img class="photo" src="' + post['image'] + '" alt="' + html.escape(post['title']) + '">' if post.get('image') else ''}
    <div class="eyebrow">JOURNAL</div>
    <div class="headline">{html.escape(post['title'])}</div>
    <div class="meta-row">{format_date_long(post['date'])}</div>
    <div class="body-copy">
      {post['body_html']}
    </div>
    {FOOTER_HTML.format(site_url=SITE_URL, site_url_display=SITE_URL.replace('https://',''))}
  </div>
</body>
</html>
"""


def render_index_page(posts):
    items = ""
    for p in posts:
        items += f"""
      <a class="post-item" href="{SITE_URL}/journal/{p['slug']}.html">
        <div class="post-item-date">{format_date_long(p['date'])}</div>
        <div class="post-item-title">{html.escape(p['title'])}</div>
        <div class="post-item-excerpt">{html.escape(p.get('excerpt',''))}</div>
      </a>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Journal — {SITE_TITLE}</title>
<meta name="description" content="{html.escape(SITE_DESCRIPTION)}">
<link rel="alternate" type="application/rss+xml" title="{SITE_TITLE}" href="{SITE_URL}/journal/feed.xml">
<style>{STYLE_BLOCK}</style>
</head>
<body>
  <div class="wrap">
    <div class="masthead">
      <a href="{SITE_URL}/"><span class="wordmark">MADE FROM EFFORT</span></a>
      <span class="bib">JOURNAL</span>
    </div>
    <div class="eyebrow">ON TRAINING &amp; CONSISTENCY</div>
    <div class="headline">The Journal</div>
    <div class="post-list">{items}
    </div>
    {FOOTER_HTML.format(site_url=SITE_URL, site_url_display=SITE_URL.replace('https://',''))}
  </div>
</body>
</html>
"""


def format_date_long(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%B %-d, %Y") if os.name != "nt" else dt.strftime("%B %d, %Y")


def rfc822(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def render_rss(posts):
    items_xml = ""
    for p in posts:
        link = f"{SITE_URL}/journal/{p['slug']}.html"
        items_xml += f"""
    <item>
      <title>{html.escape(p['title'])}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <pubDate>{rfc822(p['date'])}</pubDate>
      <description><![CDATA[{p.get('excerpt', '')}]]></description>
      <content:encoded><![CDATA[{p['body_html']}]]></content:encoded>
    </item>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{html.escape(SITE_TITLE)}</title>
    <link>{SITE_URL}/journal/</link>
    <description>{html.escape(SITE_DESCRIPTION)}</description>
    <language>en-us</language>
    <atom:link xmlns:atom="http://www.w3.org/2005/Atom" href="{SITE_URL}/journal/feed.xml" rel="self" type="application/rss+xml"/>{items_xml}
  </channel>
</rss>
"""


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def main():
    posts_glob = os.path.join(REPO_ROOT, POSTS_DIR, "*.md")
    paths = sorted(glob.glob(posts_glob))

    if not paths:
        print(f"No posts found in {POSTS_DIR}/. Add a .md file and re-run.")
        return

    posts = [parse_post(p) for p in paths]
    posts.sort(key=lambda p: p["date"], reverse=True)

    out_dir = os.path.join(REPO_ROOT, OUTPUT_DIR)
    os.makedirs(out_dir, exist_ok=True)

    for p in posts:
        page_html = render_post_page(p)
        out_path = os.path.join(out_dir, f"{p['slug']}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(page_html)
        print(f"Built {out_path}")

    index_html = render_index_page(posts)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"Built {os.path.join(out_dir, 'index.html')}")

    rss_xml = render_rss(posts)
    with open(os.path.join(out_dir, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)
    print(f"Built {os.path.join(out_dir, 'feed.xml')}")


if __name__ == "__main__":
    main()
