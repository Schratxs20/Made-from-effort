"""Protect public entity references and the residential reader journey."""
import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import unittest
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.madefromeffort.com'

def public_pages():
    for loc in ET.parse(ROOT / 'sitemap.xml').findall('.//{*}loc'):
        path = urlsplit(loc.text).path
        file = 'index.html' if path == '/' else path.lstrip('/') + ('index.html' if path.endswith('/') else '.html')
        yield loc.text, BeautifulSoup((ROOT / file).read_text(), 'html.parser')

def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)

class SchemaLinksTests(unittest.TestCase):
    def test_public_schema_references_resolve_to_named_entities(self):
        definitions, references = {}, set()
        for url, soup in public_pages():
            for script in soup.select('script[type="application/ld+json"]'):
                for node in nodes(json.loads(script.string)):
                    identity = node.get('@id', '')
                    if identity.startswith(BASE):
                        if '@type' in node:
                            definitions[identity] = node
                        else:
                            references.add(identity)
                    if node.get('@type') == 'Service':
                        self.assertEqual(node['url'], url)
        self.assertFalse(references - definitions.keys(), references - definitions.keys())
        self.assertEqual(definitions[BASE + '/#business']['name'], 'Performance Edge Training + Gym Design')
        self.assertEqual(definitions[BASE + '/#scott-schratwieser']['name'], 'Scott Schratwieser')

    def test_residential_reader_paths_use_public_canonical_urls(self):
        pages = dict(public_pages())
        paths = ['/residential-gym-design', '/project-jupiter-island', '/journal/planning-a-private-gym-before-the-floor-plan-is-finished']
        for source in paths:
            soup = BeautifulSoup(str(pages[BASE + source]), 'html.parser')
            for element in soup.select('header, footer, script'):
                element.decompose()
            links = {urljoin(BASE + source, a['href']).split('?')[0].split('#')[0] for a in soup.select('a[href]')}
            for target in paths:
                if target != source:
                    self.assertIn(BASE + target, links, source)
                    self.assertIn(BASE + target, pages)
            self.assertIn(BASE + '/contact', links, source)

    def test_open_ended_budget_has_no_structured_price_ceiling(self):
        soup = dict(public_pages())[BASE + '/residential-gym-design']
        self.assertIn('$50K–$500K+', soup.get_text())
        for script in soup.select('script[type="application/ld+json"]'):
            for node in nodes(json.loads(script.string)):
                if node.get('@type') == 'PriceSpecification':
                    self.assertNotIn('maxPrice', node)
