"""Verify visible authorship, truthful dates, and live-only related reading."""
import importlib.util
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('journal_builder', ROOT / 'scripts/build_journal.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class JournalAttributionTests(unittest.TestCase):
    def test_live_articles_identify_author_and_preserve_editorial_dates(self):
        urls = {e.text for e in ET.parse(ROOT/'sitemap.xml').findall('.//{*}loc')}
        count = 0
        for path in (ROOT/'posts').glob('*.md'):
            post = builder.parse_post(str(path))
            url = f'{builder.SITE_URL}/journal/{post["slug"]}'
            if url not in urls:
                continue
            count += 1
            rendered = (ROOT/'journal'/f'{post["slug"]}.html').read_text()
            schemas = [json.loads(x) for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>', rendered, re.S)]
            article = next(s for s in schemas if s.get('@type') == 'Article')
            self.assertIn('rel="author" href="https://www.madefromeffort.com/about"', rendered)
            self.assertEqual(article['author']['url'], builder.SITE_URL+'/about')
            self.assertEqual(article['datePublished'], post['date'])
            self.assertEqual(article.get('dateModified'), post.get('updated'))
            if post.get('updated'):
                self.assertIn('Updated <time datetime="'+post['updated']+'">', rendered)
            related = re.search(r'<nav class="related-reading".*?</nav>', rendered, re.S)
            if related:
                links = re.findall(r'href="([^"]+)"', related[0])
                self.assertTrue(all(link in urls and link != url for link in links))
                self.assertEqual(len(links), len(set(links)))
        self.assertGreater(count, 0)

    def test_update_cannot_precede_publication(self):
        with self.assertRaises(ValueError):
            builder.render_post_metadata({'slug':'test','date':'2026-10-29','updated':'2026-10-28'})

    def test_unmodified_article_does_not_acquire_build_date(self):
        post = {'title':'Example','date':'2026-01-01','slug':'example'}
        self.assertNotIn('dateModified', builder.render_schema(post, 'https://example.com/example'))
        self.assertNotIn('Updated', builder.render_post_metadata(post))
