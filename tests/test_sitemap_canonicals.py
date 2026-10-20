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
    def test_long_island_training_and_hospitality_paths(self):
        training = (ROOT / "training.html").read_text(encoding="utf-8")
        hospitality = (ROOT / "hospitality-gym-design.html").read_text(encoding="utf-8")
        contact = (ROOT / "contact.html").read_text(encoding="utf-8")
        home = (ROOT / "index.html").read_text(encoding="utf-8")
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")

        self.assertIn("<title>Long Island Personal Training &amp; Online Coaching", training)
        self.assertIn("<h1>Private Personal Training<br>on <em>Long Island, NY.</em></h1>", training)
        self.assertIn("<h2>Online &amp; Virtual <em>Training</em></h2>", training)
        self.assertIn('data-value="Online">Online / Virtual', training)
        self.assertIn("Nutrition coaching and habit tracking", training)
        self.assertIn("nutrition coaching", home)
        self.assertIn("Behavior-change coaching", training)
        self.assertIn("Behavior-change coaching", home)
        self.assertIn('<link rel="canonical" href="https://www.madefromeffort.com/hospitality-gym-design">', hospitality)
        self.assertIn("do not present a completed hotel fitness project", hospitality)
        self.assertIn('id="tile-hospitality"', contact)
        self.assertIn('value="hospitality"', contact)
        self.assertIn('href="/hospitality-gym-design"', home)
        self.assertIn('<loc>https://www.madefromeffort.com/hospitality-gym-design</loc>', sitemap)

    def test_design_articles_link_to_matching_service_pages(self):
        matches = {
            "can-you-put-a-real-gym-on-a-yacht-without-it-taking-over-the-deck": "yacht-gym-design",
            "nobody-asks-about-the-floor-until-it-s-already-a-problem": "residential-gym-design",
            "your-gym-doesn-t-need-to-impress-anyone-but-you": "residential-gym-design",
            "a-gym-isn-t-a-pile-of-good-equipment": "residential-gym-design",
            "a-gym-doesn-t-have-to-look-like-a-gym-to-train-like-one": "residential-gym-design",
            "is-the-gym-really-about-the-room-rate": "hospitality-gym-design",
            "the-best-gyms-keep-getting-redesigned": "residential-gym-design",
        }
        for slug, service in matches.items():
            with self.subTest(article=slug):
                html = (ROOT / "journal" / f"{slug}.html").read_text(encoding="utf-8")
                self.assertIn(f'href="{SITE_ORIGIN}/{service}"', html)
                self.assertIn('class="related-service"', html)
                self.assertRegex(html, r'href="https://www\.madefromeffort\.com/contact\?project=[^" ]+&amp;source=journal-')

    def test_public_internal_links_use_canonical_paths(self):
        for source in [*ROOT.glob('*.html'), *(ROOT / 'journal').glob('*.html')]:
            html = source.read_text(encoding='utf-8')
            for href in re.findall(r'href="([^"]+)"', html):
                if href.startswith(('http://', 'https://')) and not href.startswith(SITE_ORIGIN + '/'):
                    continue
                with self.subTest(source=source.name, href=href):
                    self.assertNotRegex(href.split('?', 1)[0].split('#', 1)[0], r'\.html$')

    def test_noindex_guide_is_crawlable_so_crawlers_can_read_noindex(self):
        robots = (ROOT / 'robots.txt').read_text(encoding='utf-8')
        guide = (ROOT / 'home-gym-guide.html').read_text(encoding='utf-8')
        self.assertIn('name="robots" content="noindex', guide)
        self.assertNotIn('Disallow: /home-gym-guide', robots)

    def test_contact_prefill_values_match_available_form_tiles(self):
        contact = (ROOT / 'contact.html').read_text(encoding='utf-8')
        available = set(re.findall(r'id="tile-([a-z-]+)"', contact))
        for source in [*ROOT.glob('*.html'), *(ROOT / 'journal').glob('*.html')]:
            html = source.read_text(encoding='utf-8').replace('&amp;', '&')
            for href in re.findall(r'href="([^"]+)"', html):
                if '/contact?' not in href:
                    continue
                project = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get('project')
                if project:
                    with self.subTest(source=source.name, href=href):
                        self.assertIn(project[0], available)

    def test_journal_index_links_directly_to_canonical_articles(self):
        html = (ROOT / "journal" / "index.html").read_text(encoding="utf-8")
        links = re.findall(r'<a class="post-item" href="([^"]+)"', html)
        self.assertTrue(links)
        for url in links:
            with self.subTest(url=url):
                self.assertTrue(url.startswith(f"{SITE_ORIGIN}/journal/"))
                self.assertFalse(url.endswith(".html"), url)
                article = ROOT / f"{urllib.parse.urlparse(url).path.lstrip('/')}.html"
                self.assertTrue(article.is_file(), f"Missing article for {url}")

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
