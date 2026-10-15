"""Keep XML sitemap entries aligned with Cloudflare Pages' public URLs."""

import pathlib
import json
import re
import unittest
import urllib.parse
import xml.etree.ElementTree as ET


ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE_ORIGIN = "https://www.madefromeffort.com"
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class SitemapCanonicalTests(unittest.TestCase):
    def test_sitemap_urls_are_final_public_pages(self):
        tree = ET.parse(ROOT / "sitemap.xml")
        urls = [node.text for node in tree.findall(".//s:loc", NS)]
        self.assertTrue(urls)
        self.assertEqual(len(urls), len(set(urls)), "Sitemap contains duplicate URLs")

        for url in urls:
            with self.subTest(url=url):
                parsed = urllib.parse.urlparse(url)
                self.assertEqual(f"{parsed.scheme}://{parsed.netloc}", SITE_ORIGIN)
                self.assertFalse(parsed.query or parsed.fragment)
                self.assertFalse(parsed.path.endswith(".html"), url)

                if parsed.path == "/":
                    source = ROOT / "index.html"
                elif parsed.path == "/journal/":
                    source = ROOT / "journal" / "index.html"
                else:
                    source = ROOT / f"{parsed.path.lstrip('/')}.html"

                self.assertTrue(source.is_file(), f"Missing page for {url}")
                html = source.read_text(encoding="utf-8")
                match = re.search(r'<link rel="canonical" href="([^"]+)"', html)
                self.assertIsNotNone(match, f"Missing canonical in {source}")
                self.assertEqual(match.group(1), url)

    def test_structured_data_uses_final_public_urls(self):
        for source in ROOT.glob("*.html"):
            html = source.read_text(encoding="utf-8")
            blocks = re.findall(
                r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
            )
            for block in blocks:
                with self.subTest(source=source.name):
                    data = json.loads(block)
                    self.assertNotRegex(
                        json.dumps(data),
                        r"https://www\.madefromeffort\.com/[^\"\s]+\.html(?:[\"#?]|$)",
                        "Structured data points to a redirecting .html URL",
                    )


if __name__ == "__main__":
    unittest.main()
