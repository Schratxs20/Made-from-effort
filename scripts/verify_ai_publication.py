#!/usr/bin/env python3
"""Read-only check of every published HTML/Markdown pair after deployment."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup


def fetch(origin, path, accept):
    with urlopen(Request(origin + path, headers={"Accept": accept, "User-Agent": "MadeFromEffort-PublicationCheck/1.0"}), timeout=30) as r:
        return r.status, r.headers, r.read().decode(), r.url


def verify(origin):
    status, headers, raw, _ = fetch(origin, "/ai-pages/manifest.json", "application/json")
    assert status == 200 and headers.get("Content-Type", "").split(";", 1)[0] == "application/json"
    pages = json.loads(raw)["pages"]

    def check(page):
        path = page["url"].removeprefix("https://www.madefromeffort.com")
        status, headers, raw, final = fetch(origin, path, "text/html")
        assert status == 200 and "text/html" in headers.get("Content-Type", ""), path
        assert final == origin + path, f"Unexpected redirect: {path} -> {final}"
        soup = BeautifulSoup(raw, "html.parser")
        assert soup.find("link", rel="canonical")["href"] == page["url"], path
        assert soup.find("link", rel="alternate", type="text/markdown")["href"] == page["markdown"], path
        assert soup.find("a", href="/llm-info"), path
        status, headers, md, _ = fetch(origin, page["markdown"], "text/markdown")
        assert status == 200 and "text/markdown" in headers.get("Content-Type", ""), path
        assert "noindex" in headers.get("X-Robots-Tag", ""), page["markdown"]
        assert hashlib.sha256(md.encode()).hexdigest() == page["content_sha256"], page["markdown"]
        status, headers, negotiated, _ = fetch(origin, path, "text/markdown")
        assert status == 200 and "text/markdown" in headers.get("Content-Type", ""), path
        assert "accept" in headers.get("Vary", "").lower(), path
        assert negotiated == md, f"HTML/Markdown variant mismatch: {path}"
        return path

    with ThreadPoolExecutor(max_workers=4) as pool:
        passed = list(pool.map(check, pages))
    status, _, raw, _ = fetch(origin, "/api/facts.json", "application/json")
    facts = json.loads(raw)["facts"]
    assert status == 200 and len(facts) >= 15
    print(json.dumps({"origin": origin, "verified_page_pairs": len(passed), "sourced_facts": len(facts), "status": "passed"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="https://www.madefromeffort.com")
    args = parser.parse_args()
    verify(args.origin.rstrip("/"))
