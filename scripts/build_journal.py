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
import json
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

    md_engine = markdown.Markdown(extensions=["extra", "sane_lists", "toc"])
    meta["body_html"] = md_engine.convert(body_md.strip())
    meta["toc"] = [t for t in md_engine.toc_tokens if t["level"] == 2]
    meta["faq"] = parse_faq(body_md)

    meta["source_path"] = path
    return meta


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


# ---------------------------------------------------------------------------
# FAQ extraction — for FAQPage schema (GEO/AI-citation spec, Sheet 05B)
# ---------------------------------------------------------------------------
# Convention: a "## FAQ" section where each question is its own bold
# paragraph ending in "?", immediately followed by a plain-text answer
# paragraph. Example:
#
#   ## FAQ
#
#   **How much space does this need?**
#   Enough for one full range-of-motion lift, plus clearance to move.
#
#   **Another question?**
#   Another answer.
FAQ_SECTION_RE = re.compile(r"^##\s+FAQ\s*\n(.*?)(?=^##\s+|\Z)", re.MULTILINE | re.DOTALL)
FAQ_PAIR_RE = re.compile(r"\*\*(.+?\?)\*\*\s*\n(.+?)(?=\n\s*\*\*.+?\?\*\*|\Z)", re.DOTALL)

def parse_faq(body_md):
    section = FAQ_SECTION_RE.search(body_md)
    if not section:
        return []
    pairs = FAQ_PAIR_RE.findall(section.group(1))
    faq = []
    for question, answer in pairs:
        answer_text = " ".join(answer.strip().split())
        if question.strip() and answer_text:
            faq.append({"question": question.strip(), "answer": answer_text})
    return faq


def render_schema(post, canonical_url):
    """Article + (if present) FAQPage JSON-LD — every post, no exceptions."""
    article = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post["title"],
        "description": post.get("excerpt", ""),
        "datePublished": post["date"],
        "url": canonical_url,
        "author": {"@type": "Person", "name": "Scott Schratwieser"},
        "publisher": {"@type": "Organization", "name": SITE_TITLE, "url": SITE_URL},
    }
    blocks = [f'<script type="application/ld+json">{json.dumps(article)}</script>']

    if post.get("faq"):
        faq_schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": qa["question"],
                    "acceptedAnswer": {"@type": "Answer", "text": qa["answer"]},
                }
                for qa in post["faq"]
            ],
        }
        blocks.append(f'<script type="application/ld+json">{json.dumps(faq_schema)}</script>')

    return "\n".join(blocks)


# ---------------------------------------------------------------------------
# Templates — matches the Made From Effort design system
# ---------------------------------------------------------------------------
STYLE_BLOCK = """
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400;1,600&family=Inter:wght@300;400;500;600&display=swap');
  * { box-sizing: border-box; }
  body { margin:0; padding:0; background:#FAF9F6; font-family:'Inter',-apple-system,sans-serif; color:#1C1C1A; }
  .wrap { max-width:760px; margin:0 auto; background:#FAF9F6; }
  .masthead { padding:32px 40px; border-bottom:1px solid #E2E0D9; display:flex; align-items:center; justify-content:space-between; }
  .masthead a { text-decoration:none; color:#1C1C1A; }
  .wordmark { font-family:'Playfair Display',serif; font-style:italic; font-weight:400; font-size:24px; color:#1C1C1A; }
  .wordmark-sub { font-family:'Inter',sans-serif; font-weight:500; font-size:10px; letter-spacing:2px; color:#A6A39B; text-transform:uppercase; margin-top:2px; }
  .nav-tag { font-family:'Inter',sans-serif; font-weight:500; font-size:11px; letter-spacing:1.5px; color:#57677A; text-transform:uppercase; border:1px solid #57677A; padding:6px 14px; }
  .photo { width:100%; display:block; }
  .eyebrow { padding:40px 40px 0; font-family:'Inter',sans-serif; font-weight:500; font-size:11px; letter-spacing:2px; color:#A6A39B; text-transform:uppercase; }
  .headline { padding:10px 40px 30px; font-family:'Playfair Display',serif; font-weight:400; font-size:38px; line-height:1.2; color:#1C1C1A; }
  .headline em { font-style:italic; }
  .body-copy { padding:0 40px; font-family:'Inter',sans-serif; font-weight:300; font-size:17px; line-height:1.75; color:#4A4944; }
  .body-copy p { margin:0 0 22px; }
  .body-copy h2 { font-family:'Playfair Display',serif; font-weight:400; font-size:26px; color:#1C1C1A; margin:36px 0 16px; }
  .body-copy blockquote { font-family:'Playfair Display',serif; font-style:italic; font-weight:400; font-size:23px; line-height:1.45; color:#1C1C1A; padding:6px 0 6px 24px; border-left:2px solid #57677A; margin:12px 0 30px; }
  .body-copy strong { color:#1C1C1A; font-weight:500; }
  .body-copy img { width:100%; display:block; margin:0 0 30px; }
  .body-copy ol, .body-copy ul { padding-left: 22px; }
  .body-copy li { margin-bottom: 12px; }
  .meta-row { padding:0 40px 24px; font-family:'Inter',sans-serif; font-weight:400; font-size:12px; letter-spacing:1px; color:#A6A39B; text-transform:uppercase; }
  .divider { border:none; border-top:1px solid #E2E0D9; margin:8px 40px 32px; }
  .cta-wrap { padding:8px 40px 44px; }
  .cta { display:inline-block; font-family:'Inter',sans-serif; font-weight:500; font-size:12px; letter-spacing:1.5px; text-transform:uppercase; color:#FAF9F6; background:#1C1C1A; padding:16px 32px; text-decoration:none; }
  .footer { background:#F1EFEA; padding:28px 40px; border-top:1px solid #E2E0D9; }
  .footer-links { display:flex; gap:32px; padding-bottom:18px; margin-bottom:16px; border-bottom:1px solid #E2E0D9; }
  .footer-links a { font-family:'Inter',sans-serif; font-weight:500; font-size:11px; letter-spacing:1.5px; color:#1C1C1A; text-decoration:none; text-transform:uppercase; }
  .footer-fine { font-family:'Inter',sans-serif; font-weight:300; font-size:12px; line-height:1.7; color:#A6A39B; }
  .footer-fine a { color:#A6A39B; text-decoration:underline; }
  /* index list */
  .post-list { padding:0 40px 40px; }
  .post-item { display:block; padding:28px 0; border-top:1px solid #E2E0D9; text-decoration:none; }
  .post-item:first-child { border-top:none; }
  .post-item-date { font-family:'Inter',sans-serif; font-weight:500; font-size:11px; letter-spacing:1.5px; color:#57677A; text-transform:uppercase; }
  .post-item-title { font-family:'Playfair Display',serif; font-weight:400; font-size:26px; color:#1C1C1A; margin:8px 0; }
  .post-item-excerpt { font-family:'Inter',sans-serif; font-weight:300; font-size:15px; color:#6B6B66; line-height:1.6; }
"""

FOOTER_HTML = """
    <div class="footer">
      <div class="footer-links">
        <a href="{site_url}/training.html">TRAINING</a>
        <a href="{site_url}/#portfolio">PORTFOLIO</a>
        <a href="{site_url}/#services">SERVICES</a>
      </div>
      <div class="footer-fine">
        Scott Schratwieser &middot; Long Island, NY<br>
        <a href="{site_url}">{site_url_display}</a>
      </div>
    </div>
"""

# Fallback CTA destinations if a post doesn't set cta_link explicitly.
# Matched against cta_text (case-insensitive, substring match).
CTA_LINK_DEFAULTS = {
    "train with me": f"{SITE_URL}/training.html",
    "start a project": f"{SITE_URL}/#contact",
}
CTA_LINK_FALLBACK = f"{SITE_URL}/#contact"

def resolve_cta_link(post):
    if post.get("cta_link"):
        return post["cta_link"]
    cta_text = post.get("cta_text", "Start a Project").lower()
    for key, link in CTA_LINK_DEFAULTS.items():
        if key in cta_text:
            return link
    return CTA_LINK_FALLBACK


def render_post_page(post):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(post['title'])} — {SITE_TITLE}</title>
<meta name="description" content="{html.escape(post.get('excerpt',''))}">
<link rel="canonical" href="{SITE_URL}/journal/{post['slug']}.html">
{render_schema(post, f"{SITE_URL}/journal/{post['slug']}.html")}
<style>{STYLE_BLOCK}</style>
</head>
<body>
  <div class="wrap">
    <div class="masthead">
      <a href="{SITE_URL}/">
        <div class="wordmark">Made From Effort</div>
        <div class="wordmark-sub">Performance Edge Training + Gym Design</div>
      </a>
      <a href="{SITE_URL}/journal/"><span class="nav-tag">Journal</span></a>
    </div>
    {'<img class="photo" src="' + post['image'] + '" alt="' + html.escape(post['title']) + '">' if post.get('image') else ''}
    <div class="eyebrow">Journal</div>
    <div class="headline">{html.escape(post['title'])}</div>
    <div class="meta-row">{format_date_long(post['date'])}</div>
    <div class="body-copy">
      {post['body_html']}
    </div>
    <div class="cta-wrap">
      <a href="{resolve_cta_link(post)}" class="cta">{html.escape(post.get('cta_text', 'Start a Project'))}</a>
    </div>
    {FOOTER_HTML.format(site_url=SITE_URL, site_url_display=SITE_URL.replace('https://',''))}
  </div>
</body>
</html>
"""


def render_email_ready_page(post, link):
    """A standalone page with nothing on it but what belongs in the email —
    no masthead, no site nav, no site footer. Built for one workflow: click
    Copy, then paste straight into a new Beehiiv post. The copy button
    grabs only #emailContent, so the toolbar/subject-line above it can
    never end up in the pasted result even by accident. The subject line
    is the only thing typed by hand (Beehiiv's subject field is separate
    from the pasted body)."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(post['title'])} — Email-ready copy</title>
<meta name="robots" content="noindex">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400;1,600&family=Inter:wght@300;400;500;600&display=swap');
  * {{ box-sizing: border-box; }}
  body {{ margin:0; padding:0; background:#FAF9F6; font-family:'Inter',-apple-system,sans-serif; color:#1C1C1A; }}
  .toolbar {{ position:sticky; top:0; z-index:10; background:#1C1C1A; padding:16px 20px; display:flex; align-items:center; justify-content:center; gap:16px; flex-wrap:wrap; }}
  #copyBtn {{ font-family:'Inter',sans-serif; font-weight:500; font-size:13px; letter-spacing:1px; text-transform:uppercase; color:#1C1C1A; background:#FAF9F6; border:none; padding:12px 24px; cursor:pointer; }}
  #copyBtn:hover {{ background:#fff; }}
  .toolbar-note {{ font-family:'Inter',sans-serif; font-size:12px; color:#A6A39B; }}
  .subject-line {{ max-width:600px; margin:0 auto; padding:20px 32px 0; font-family:'Inter',sans-serif; font-size:13px; color:#57677A; }}
  .subject-line b {{ color:#1C1C1A; }}
  .wrap {{ max-width:600px; margin:0 auto; background:#FAF9F6; }}
  .eyebrow {{ padding:24px 32px 0; font-family:'Inter',sans-serif; font-weight:500; font-size:11px; letter-spacing:2px; color:#A6A39B; text-transform:uppercase; }}
  .headline {{ padding:8px 32px 20px; font-family:'Playfair Display',serif; font-weight:400; font-size:30px; line-height:1.2; color:#1C1C1A; }}
  .meta-row {{ padding:0 32px 20px; font-family:'Inter',sans-serif; font-weight:400; font-size:12px; letter-spacing:1px; color:#A6A39B; text-transform:uppercase; }}
  .body-copy {{ padding:0 32px 8px; font-family:'Inter',sans-serif; font-weight:300; font-size:16px; line-height:1.72; color:#4A4944; }}
  .body-copy p {{ margin:0 0 20px; }}
  .body-copy h2 {{ font-family:'Playfair Display',serif; font-weight:400; font-size:23px; color:#1C1C1A; margin:32px 0 14px; }}
  .body-copy blockquote {{ font-family:'Playfair Display',serif; font-style:italic; font-weight:400; font-size:20px; line-height:1.45; color:#1C1C1A; padding:4px 0 4px 20px; border-left:2px solid #57677A; margin:10px 0 26px; }}
  .body-copy strong {{ color:#1C1C1A; font-weight:500; }}
  .body-copy ol, .body-copy ul {{ padding-left: 20px; }}
  .body-copy li {{ margin-bottom: 10px; }}
</style>
</head>
<body>
  <div class="toolbar">
    <button id="copyBtn" type="button">Copy For Beehiiv</button>
    <span class="toolbar-note">Then: new post in Beehiiv &rarr; paste into the body</span>
  </div>
  <div class="subject-line">Subject line (type this into Beehiiv separately): <b>{html.escape(post['title'])}</b></div>
  <div class="wrap" id="emailContent">
    <div class="eyebrow">Journal</div>
    <div class="headline">{html.escape(post['title'])}</div>
    <div class="meta-row">{format_date_long(post['date'])}</div>
    <div class="body-copy">
      {post['body_html']}
    </div>
    <div class="body-copy">
      {render_email_footer(post, link)}
    </div>
  </div>
  <script>
    document.getElementById('copyBtn').addEventListener('click', async function() {{
      var btn = this;
      var original = btn.textContent;
      var container = document.getElementById('emailContent');
      var htmlContent = container.outerHTML;
      var textContent = container.innerText;
      try {{
        var item = new ClipboardItem({{
          'text/html': new Blob([htmlContent], {{type: 'text/html'}}),
          'text/plain': new Blob([textContent], {{type: 'text/plain'}})
        }});
        await navigator.clipboard.write([item]);
        btn.textContent = 'Copied — paste into Beehiiv';
      }} catch (err) {{
        btn.textContent = 'Copy failed — select the page manually';
      }}
      setTimeout(function() {{ btn.textContent = original; }}, 3000);
    }});
  </script>
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
      <a href="{SITE_URL}/">
        <div class="wordmark">Made From Effort</div>
        <div class="wordmark-sub">Performance Edge Training + Gym Design</div>
      </a>
    </div>
    <div class="eyebrow">On Training &amp; Consistency</div>
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


def render_email_footer(post, link):
    """Appended to every RSS item's content:encoded — this is what Beehiiv's
    RSS-to-Send pulls into the email body. Inline styles only: once this
    passes through Beehiiv's importer, a shared <style> block can't be
    relied on to survive, but inline styles do. This block is what makes
    'always link back to the site + always show Instagram' true regardless
    of whatever template settings get changed inside Beehiiv later."""
    cta_link = resolve_cta_link(post)
    cta_text = html.escape(post.get('cta_text', 'Start a Project'))
    return f"""
<div style="margin-top:40px;padding-top:28px;border-top:1px solid #E2E0D9;font-family:Inter,-apple-system,sans-serif;">
  <p style="margin:0 0 20px;">
    <a href="{link}" style="display:inline-block;font-family:Inter,-apple-system,sans-serif;font-weight:500;font-size:12px;letter-spacing:1.5px;text-transform:uppercase;color:#FAF9F6;background:#1C1C1A;padding:14px 28px;text-decoration:none;">Read It On The Site</a>
  </p>
  <p style="margin:0 0 14px;">
    <a href="{cta_link}" style="color:#1C1C1A;font-weight:500;font-size:15px;text-decoration:underline;">{cta_text} &rarr;</a>
  </p>
  <p style="margin:0;font-size:12px;letter-spacing:1.5px;text-transform:uppercase;color:#A6A39B;">
    Follow along &middot; <a href="https://www.instagram.com/scottschrat" style="color:#57677A;text-decoration:none;font-weight:500;">@SCOTTSCHRAT on Instagram</a>
  </p>
</div>"""


def render_rss(posts):
    items_xml = ""
    for p in posts:
        link = f"{SITE_URL}/journal/{p['slug']}.html"
        email_body = p['body_html'] + render_email_footer(p, link)
        items_xml += f"""
    <item>
      <title>{html.escape(p['title'])}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <pubDate>{rfc822(p['date'])}</pubDate>
      <description><![CDATA[{p.get('excerpt', '')}]]></description>
      <content:encoded><![CDATA[{email_body}]]></content:encoded>
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
        link = f"{SITE_URL}/{OUTPUT_DIR}/{p['slug']}.html"

        page_html = render_post_page(p)
        out_path = os.path.join(out_dir, f"{p['slug']}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(page_html)
        print(f"Built {out_path}")

        email_html = render_email_ready_page(p, link)
        email_out_path = os.path.join(out_dir, f"{p['slug']}-email.html")
        with open(email_out_path, "w", encoding="utf-8") as f:
            f.write(email_html)
        print(f"Built {email_out_path}  <-- open this one to copy/paste into Beehiiv")

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
