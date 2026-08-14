#!/usr/bin/env python3
"""Checks the generated index.html — the manual pre-commit ritual, automated.

../CLAUDE.md says: "verify inline JS before committing: extract <script> blocks →
node --check". Doing that by hand means it gets skipped on a tired evening, and a
syntax error in inline JS is invisible until the page is live (the browser just
stops running the script — no build error, no 404, nothing).

So: parse index.html, hand every inline <script> to `node --check`, and parse the
JSON-LD block with the stdlib. No third-party dependencies.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"

SCRIPT_RE = re.compile(r"<script([^>]*)>(.*?)</script>", re.S)
NODE = shutil.which("node")


def inline_scripts():
    """(attrs, body) for every <script> whose body lives in the page itself."""
    if not INDEX.exists():
        return []
    html = INDEX.read_text(encoding="utf-8")
    return [(m.group(1), m.group(2)) for m in SCRIPT_RE.finditer(html)
            if "src=" not in m.group(1)]


def js_blocks():
    return [body for attrs, body in inline_scripts()
            if "application/ld+json" not in attrs and body.strip()]


def jsonld_blocks():
    return [body for attrs, body in inline_scripts() if "application/ld+json" in attrs]


@unittest.skipUnless(INDEX.exists(), "index.html not built yet")
class TestGeneratedPage(unittest.TestCase):
    def test_page_has_inline_scripts_to_check(self):
        """If this ever hits zero, the extraction regex broke and every check below
        would silently pass while verifying nothing."""
        self.assertGreater(len(js_blocks()), 0)

    @unittest.skipUnless(NODE, "node not installed")
    def test_inline_javascript_parses(self):
        for idx, body in enumerate(js_blocks()):
            with self.subTest(script=idx):
                with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                                 encoding="utf-8") as fh:
                    fh.write(body)
                    tmp = fh.name
                try:
                    r = subprocess.run([NODE, "--check", tmp],
                                       capture_output=True, text=True)
                    self.assertEqual(r.returncode, 0, f"node --check failed:\n{r.stderr}")
                finally:
                    Path(tmp).unlink(missing_ok=True)

    def test_json_ld_is_valid_json(self):
        """Structured data fails silently too — search engines just drop it."""
        blocks = jsonld_blocks()
        self.assertGreater(len(blocks), 0, "expected a JSON-LD block in <head>")
        for idx, body in enumerate(blocks):
            with self.subTest(block=idx):
                json.loads(body)


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
