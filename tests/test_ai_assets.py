import json
import re
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_ai_assets import build, page_markdown, markdown_path
from bs4 import BeautifulSoup


class AICopyTests(unittest.TestCase):
    def test_source_sentences_headings_tables_and_links_survive_without_chrome(self):
        source = '''<html><head><title>Example page</title></head><body>
        <header>HEADER NAVIGATION</header><nav>NAVIGATION</nav><main>
        <h1>The room matters.</h1><p>Keep <em>every</em> original sentence.</p>
        <h2>Clearance</h2><ul><li>One useful list item.</li></ul>
        <table><tr><th>Model</th><th>Height</th></tr><tr><td>A</td><td>Check the specification.</td></tr></table>
        <p>Read <a href="/training">the coaching page</a>.</p>
        <form>PRIVATE FORM FIELDS<input value="SECRET"></form><button>CLICK THIS</button>
        </main><footer>FOOTER LINKS</footer><script>TRACKING</script></body></html>'''
        copy = page_markdown(source, "https://www.madefromeffort.com/example")
        for required in ["# Example page", "# The room matters.", "## Clearance", "Keep *every* original sentence.", "One useful list item.", "Check the specification.", "[the coaching page](https://www.madefromeffort.com/training)"]:
            self.assertIn(required, copy)
        for removed in ["HEADER NAVIGATION", "NAVIGATION", "PRIVATE FORM FIELDS", "SECRET", "CLICK THIS", "FOOTER LINKS", "TRACKING"]:
            self.assertNotIn(removed, copy)

    def test_generated_public_copies_are_current(self):
        pages = build(check=True)
        self.assertGreaterEqual(len(pages), 40)
        for page in pages:
            self.assertNotIn("home-gym-guide", page["url"])
            self.assertNotIn("-email", page["url"])
            copy = (ROOT / page["markdown"].lstrip("/")).read_text()
            self.assertIn(page["url"], copy)
            source = (ROOT / page["source"]).read_text()
            self.assertIn('href="/llm-info"', source)
            self.assertIn(f'href="{page["markdown"]}"', source)
            self.assertEqual(len(re.findall(r'^# ', copy, re.M)), 1 + len(BeautifulSoup(source, 'html.parser').find_all('h1')), page['url'])
        self.assertTrue((ROOT / "api/facts.json").is_file())

    def test_fact_sources_are_dated_and_public(self):
        data = json.loads((ROOT / "api/facts.json").read_text())
        self.assertGreaterEqual(len(data["facts"]), 15)
        for fact in data["facts"]:
            self.assertRegex(fact["checked"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertTrue(fact["source"].startswith("https://www.madefromeffort.com/"))
            self.assertNotIn("Biltmore", fact["text"])

    def test_paths_do_not_collide(self):
        self.assertEqual(markdown_path("https://www.madefromeffort.com/"), "/ai-pages/index.md")
        self.assertEqual(markdown_path("https://www.madefromeffort.com/journal/"), "/ai-pages/journal.md")

    def test_content_header_is_preserved_but_navigation_header_is_removed(self):
        source = '<html><head><title>Hotel gym design</title></head><body><header><nav>MENU</nav></header><header class="hero"><h1>A gym for the property.</h1><p>Keep this original introduction to the service and its training-room constraints.</p></header><section><h2>Plan the room</h2><p>Original body.</p></section></body></html>'
        copy = page_markdown(source, "https://www.madefromeffort.com/hospitality-gym-design")
        self.assertIn('# A gym for the property.', copy)
        self.assertIn('Keep this original introduction', copy)
        self.assertNotIn('MENU', copy)


if __name__ == "__main__":
    unittest.main()
