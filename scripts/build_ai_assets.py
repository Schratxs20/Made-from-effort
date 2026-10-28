#!/usr/bin/env python3
"""Build faithful text copies only from sitemap-listed, indexable HTML.

Run after build_journal.py (which calls this), or directly after static edits.
--check fails if generated assets or the per-page inventory are out of date.
No network, AI rewriting, invented facts, or user-agent discrimination.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup, Comment
from markdownify import markdownify

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://www.madefromeffort.com"
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
START = "<!-- BEGIN GENERATED AI PAGE INDEX -->"
END = "<!-- END GENERATED AI PAGE INDEX -->"
FACT_LINK = '<a href="/llm-info">Business facts</a>'


def source_for(url, root=ROOT):
    path = urlparse(url).path
    if path.endswith("/"):
        return root / path.lstrip("/") / "index.html"
    return root / (path.lstrip("/") + ".html")


def markdown_path(url):
    path = urlparse(url).path
    return "/ai-pages/" + (path.strip("/") or "index") + ".md"


def page_markdown(raw, url):
    """Preserve source wording/headings/links, removing only presentation/UI."""
    soup = BeautifulSoup(raw, "html.parser")
    title = soup.title.get_text(" ", strip=True)
    # Remove chrome even when old pages do not use semantic landmarks.
    for node in soup.select(
        'script, style, noscript, nav, header:not(:has(h1)), footer, button, form, input, '
        'textarea, select, svg, template, [role="dialog"], [aria-hidden="true"], '
        '.masthead, .footer, .nav, .step-bar, .form-card, .panel, '
        '#popup-overlay, .lightbox, .lightbox-overlay, .breadcrumb, .breadcrumbs'
    ):
        node.decompose()
    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()
    # Several legacy pages put their editorial hero header before <main>.
    # Keep the cleaned body so those original headings/intros survive too.
    content = soup.body
    if not content:
        raise ValueError(f"No body content: {url}")
    for node in content.find_all(True):
        for attr in ("href", "src", "poster"):
            if node.get(attr):
                node[attr] = urljoin(url, node[attr])
    body = markdownify(str(content), heading_style="ATX", bullets="-")
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if len(body) < 80:
        raise ValueError(f"Insufficient main text: {url}")
    return f"# {title}\n\nSource: [{url}]({url})\n\n{body}\n"


def facts_assets(root=ROOT):
    data = json.loads((root / "config/business-facts.json").read_text())
    items = []
    for fact in data["facts"]:
        path = fact["source_path"]
        source = (root / path.lstrip("/")) if path.endswith(".txt") else source_for(SITE + path, root)
        raw = source.read_text()
        evidence = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True) if source.suffix == ".html" else raw
        if " ".join(fact["evidence"].split()) not in " ".join(evidence.split()):
            raise ValueError(f"Fact evidence no longer matches its source: {fact['id']}")
        checked = fact["checked"]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", checked):
            raise ValueError(f"Missing checked date: {fact['id']}")
        item = {k: fact[k] for k in ("id", "text", "checked")}
        item["source"] = SITE + path
        items.append(item)
    rows = "\n".join(
        f'<li id="{html.escape(f["id"])}"><p>{html.escape(f["text"])}</p>'
        f'<p class="source"><a href="{html.escape(f["source"])}">Source</a> · '
        f'Checked <time datetime="{f["checked"]}">{f["checked"]}</time></p></li>'
        for f in items
    )
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Business Facts | Made From Effort</title>
<meta name="description" content="Sourced facts about Performance Edge Training + Gym Design, Made From Effort, Scott Schratwieser, services, and project scope.">
<link rel="canonical" href="{SITE}/llm-info">
<style>
:root{{color-scheme:light;--ink:#181816;--muted:#69685f;--paper:#fafaf8;--rule:#dedbd4}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.7 Arial,sans-serif}}header,main,footer{{max-width:960px;margin:auto;padding:28px 24px}}header{{border-bottom:1px solid var(--rule);display:flex;gap:24px;justify-content:space-between;flex-wrap:wrap}}a{{color:inherit;text-underline-offset:4px}}.brand{{font:italic 25px Georgia,serif;text-decoration:none}}nav{{display:flex;gap:20px;flex-wrap:wrap}}main{{padding-top:68px;padding-bottom:72px}}h1{{font:400 clamp(42px,8vw,76px)/1.1 Georgia,serif;margin:0 0 24px}}.intro{{max-width:750px;color:var(--muted)}}h2{{font:400 32px Georgia,serif;margin:48px 0 20px}}ol{{padding-left:24px}}li{{padding:16px 0;border-bottom:1px solid var(--rule)}}li p{{margin:0 0 8px}}.source,footer{{font-size:13px;color:var(--muted)}}footer{{border-top:1px solid var(--rule)}}
</style><script src="/site-events.js?v=2" defer></script></head><body>
<header><a class="brand" href="/">Made From Effort</a><nav aria-label="Main navigation"><a href="/about">About Scott</a><a href="/residential-gym-design">Gym design</a><a href="/contact">Start a project</a></nav></header>
<main><h1>Business facts</h1><p class="intro">Official business information about Performance Edge Training + Gym Design and Made From Effort. Each fact links to the page that supports it and records when it was checked. These are business-published statements, not independent credential verification.</p>
<p><a href="/api/facts.json">Download the sourced facts as JSON</a></p>
<h2>The business, services, and work</h2><ol>{rows}</ol>
<h2>Discuss your project</h2><p><a href="/contact">Inquire about gym design</a> or <a href="/training#training-form">ask about coaching</a>. Project fees, scope, and availability are confirmed through a conversation. Training and coaching are separate from gym design.</p>
</main><footer><nav aria-label="Footer"><a href="/">Home</a><a href="/about">About</a><a href="/privacy">Privacy</a><a href="/llms.txt">Site guide</a>{FACT_LINK}</nav></footer></body></html>
'''
    return page, json.dumps({"business": data["name"], "website": SITE, "facts": items}, indent=2, ensure_ascii=False) + "\n"


def add_discovery_links(raw, url):
    alternate = f'<link rel="alternate" type="text/markdown" href="{markdown_path(url)}" title="Markdown version">'
    raw = re.sub(r'<link rel="alternate" type="text/markdown"[^>]*>\n?', "", raw)
    raw = raw.replace("</head>", alternate + "\n</head>", 1)
    if 'href="/llm-info"' not in raw:
        footer = re.search(r'<footer\b[^>]*>.*?</footer>', raw, re.S | re.I)
        if footer:
            segment = footer.group()
            if 'class="foot-links"' in segment:
                segment = segment.replace('</ul>', '<li>' + FACT_LINK + '</li></ul>', 1)
            elif '</nav>' in segment:
                segment = segment.replace('</nav>', FACT_LINK + '</nav>', 1)
            else:
                segment = segment.replace('</footer>', '<span style="font-size:12px">' + FACT_LINK + '</span></footer>')
            raw = raw[:footer.start()] + segment + raw[footer.end():]
        elif 'class="footer-links"' in raw:
            raw = raw.replace('<div class="footer-links">', '<div class="footer-links">\n        ' + FACT_LINK, 1)
        else:
            raw = raw.replace('</body>', '<footer style="padding:24px;text-align:center;font:12px Arial,sans-serif">' + FACT_LINK + '</footer>\n</body>')
    return raw


def build(root=ROOT, check=False):
    expected = {}
    fact_html, fact_json = facts_assets(root)
    expected[root / "llm-info.html"] = fact_html
    expected[root / "api/facts.json"] = fact_json
    urls = [n.text for n in ET.parse(root / "sitemap.xml").findall(".//s:loc", NS)]
    if len(urls) != len(set(urls)):
        raise ValueError("Duplicate public URLs")
    copies, inventory = {}, []
    for url in urls:
        if not url.startswith(SITE + "/") or urlparse(url).query or urlparse(url).fragment:
            raise ValueError(f"Unexpected public URL: {url}")
        source = source_for(url, root)
        raw = expected.get(source, source.read_text() if source.exists() else "")
        soup = BeautifulSoup(raw, "html.parser")
        canonical = soup.find("link", rel="canonical")
        if not canonical or canonical.get("href") != url:
            raise ValueError(f"Sitemap/canonical mismatch: {url}")
        if any("noindex" in m.get("content", "").lower() for m in soup.find_all("meta", attrs={"name": re.compile(r"^(robots|googlebot)$", re.I)})):
            raise ValueError(f"Noindex page in public manifest: {url}")
        raw = add_discovery_links(raw, url)
        expected[source] = raw
        copy = page_markdown(raw, url)
        md_path = markdown_path(url)
        expected[root / md_path.lstrip("/")] = copy
        copies[urlparse(url).path] = copy
        inventory.append({"url": url, "source": str(source.relative_to(root)), "markdown": md_path,
                          "title": soup.title.get_text(" ", strip=True),
                          "content_sha256": hashlib.sha256(copy.encode()).hexdigest(),
                          "title_test": "awaiting_eligible_baseline",
                          "crawler_review": "weekly_by_canonical_url",
                          "facts": SITE + "/llm-info"})
    # An omitted new static page must fail the build, not disappear silently.
    for source in root.glob("*.html"):
        soup = BeautifulSoup(expected.get(source, source.read_text()), "html.parser")
        canonical = soup.find("link", rel="canonical")
        noindex = soup.find("meta", attrs={"name": "robots", "content": re.compile("noindex", re.I)})
        if canonical and not noindex and canonical.get("href") not in urls:
            raise ValueError(f"Public page missing from sitemap: {source.name}")
    expected[root / "_ai-page-data.js"] = "// Generated by scripts/build_ai_assets.py. Do not edit.\nexport const PAGE_MARKDOWN = " + json.dumps(copies, ensure_ascii=False, indent=2) + ";\n"
    expected[root / "ai-pages/manifest.json"] = json.dumps({"pages": inventory}, ensure_ascii=False, indent=2) + "\n"
    llms = (root / "llms.txt").read_text()
    section = START + "\n\n## Clean Markdown copies of every public page\n\n" + "\n".join(
        f'- [{p["title"]}]({SITE}{p["markdown"]})' for p in inventory
    ) + f'\n\n- [Sourced business facts]({SITE}/llm-info)\n- [Facts JSON]({SITE}/api/facts.json)\n\n' + END
    if START in llms:
        llms = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: section, llms, flags=re.S)
    else:
        llms = llms.rstrip() + "\n\n" + section + "\n"
    expected[root / "llms.txt"] = llms
    changed = [str(path.relative_to(root)) for path, text in expected.items() if not path.exists() or path.read_text() != text]
    stale = set((root / "ai-pages").rglob("*.md")) - set(expected)
    if check:
        if changed or stale:
            raise ValueError("Stale AI assets; run scripts/build_ai_assets.py: " + ", ".join(changed + [str(p.relative_to(root)) for p in stale]))
    else:
        for path, text in expected.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        for path in stale:
            path.unlink()  # generated copies of pages removed from the public sitemap
    print(f"{'Checked' if check else 'Built'} {len(inventory)} public-page Markdown copies; {len(changed)} changed files")
    return inventory


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    build(check=args.check)
