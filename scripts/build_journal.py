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
# Config — ed
