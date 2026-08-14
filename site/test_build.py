#!/usr/bin/env python3
"""Unit tests for build.py — stdlib only, so the zero-dependency rule still holds.

    python3 -m unittest discover -s site -p 'test_*.py'

Scope: the pure functions (no I/O, no network), plus one integration test for the
`visibility: public` safety belt — the invariant that keeps private notes out of the
published page. Every case here is something that has broken, or that would break
silently if it did (see ../CLAUDE.md "Gotchas learned the hard way").
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build  # noqa: E402


class TestParseFrontmatter(unittest.TestCase):
    def test_no_frontmatter_passes_through(self):
        meta, body = build.parse_frontmatter("# Just a note\n\ntext")
        self.assertEqual(meta, {})
        self.assertEqual(body, "# Just a note\n\ntext")

    def test_basic_keys(self):
        meta, body = build.parse_frontmatter("---\nid: foo\ntitle: Foo\n---\nbody text")
        self.assertEqual(meta["id"], "foo")
        self.assertEqual(meta["title"], "Foo")
        self.assertEqual(body, "body text")

    def test_bracket_list_becomes_list(self):
        meta, _ = build.parse_frontmatter("---\ntags: [a, b , c]\n---\nx")
        self.assertEqual(meta["tags"], ["a", "b", "c"])

    def test_empty_bracket_list(self):
        meta, _ = build.parse_frontmatter("---\ntags: []\n---\nx")
        self.assertEqual(meta["tags"], [])

    def test_value_may_contain_colons(self):
        """URLs are the common case — only the first colon separates key from value."""
        meta, _ = build.parse_frontmatter("---\nsource: https://example.com/a:b\n---\nx")
        self.assertEqual(meta["source"], "https://example.com/a:b")

    def test_unterminated_block_is_not_frontmatter(self):
        raw = "---\nid: foo\nnever closed"
        meta, body = build.parse_frontmatter(raw)
        self.assertEqual(meta, {})
        self.assertEqual(body, raw)

    def test_lines_without_colon_are_skipped(self):
        meta, _ = build.parse_frontmatter("---\nid: foo\njust noise\n---\nx")
        self.assertEqual(meta, {"id": "foo"})

    def test_horizontal_rule_in_body_survives(self):
        """Notes use `---` as a divider; only the first two may be the frontmatter fence."""
        _, body = build.parse_frontmatter("---\nid: foo\n---\nintro\n\n---\n\nmore")
        self.assertIn("more", body)


class TestInline(unittest.TestCase):
    def test_code_span(self):
        self.assertEqual(build._inline("use `x` here"), "use <code>x</code> here")

    def test_bold_is_consumed_before_italic(self):
        """The italic rule runs after bold. If that order ever flips, `**a**` renders as
        `<em>` wrapping a stray asterisk instead of `<strong>` — silently, on every page."""
        self.assertEqual(build._inline("**a**"), "<strong>a</strong>")

    def test_bold_and_italic_together(self):
        out = build._inline("**bold** and *it*")
        self.assertIn("<strong>bold</strong>", out)
        self.assertIn("<em>it</em>", out)
        self.assertNotIn("*", out)

    def test_html_is_escaped(self):
        self.assertEqual(build._inline("<script>"), "&lt;script&gt;")

    def test_ampersand_is_escaped(self):
        self.assertEqual(build._inline("a & b"), "a &amp; b")

    def test_image(self):
        out = build._inline("![alt text](pic.png)")
        self.assertIn('<img src="pic.png"', out)
        self.assertIn('alt="alt text"', out)

    def test_external_link_opens_safely(self):
        """rel=noopener is a security property, not styling — assert it explicitly."""
        out = build._inline("[t](https://example.com)")
        self.assertIn('href="https://example.com"', out)
        self.assertIn('rel="noopener"', out)


class TestMdToHtml(unittest.TestCase):
    def test_fenced_code_carries_language_class(self):
        out = build.md_to_html("```python\nx = 1\n```")
        self.assertIn('<pre><code class="lang-python">', out)
        self.assertIn("x = 1", out)

    def test_fenced_code_without_language(self):
        self.assertIn("<pre><code>", build.md_to_html("```\nplain\n```"))

    def test_code_block_content_is_escaped(self):
        self.assertIn("&lt;div&gt;", build.md_to_html("```\n<div>\n```"))

    def test_heading_shifts_down_one_level(self):
        """Notes start at `#`, but the page already owns h1 — headings shift down."""
        self.assertIn("<h2>Title</h2>", build.md_to_html("# Title"))

    def test_heading_caps_at_h6(self):
        self.assertIn("<h6>Deep</h6>", build.md_to_html("###### Deep"))

    def test_table(self):
        out = build.md_to_html("| A | B |\n|---|---|\n| 1 | 2 |")
        self.assertIn("<table>", out)
        self.assertIn("<th>A</th>", out)
        self.assertIn("<td>1</td>", out)

    def test_table_needs_a_real_separator_row(self):
        """Two piped lines in a row are not a table — without this check, ordinary
        prose containing `|` would be swallowed into a bogus <table>."""
        out = build.md_to_html("| A | B |\n| C | D |")
        self.assertNotIn("<table>", out)

    def test_blockquote(self):
        self.assertIn("<blockquote>", build.md_to_html("> quoted"))

    def test_unordered_list_folds_lazy_continuation(self):
        """A wrapped bullet is one item, not an item plus a stray paragraph."""
        out = build.md_to_html("- first line\n  wrapped on\n- second")
        self.assertIn("<li>first line wrapped on</li>", out)
        self.assertIn("<li>second</li>", out)

    def test_ordered_list_folds_lazy_continuation(self):
        out = build.md_to_html("1. first line\n   wrapped on\n2. second")
        self.assertIn("<li>first line wrapped on</li>", out)

    def test_paragraph(self):
        self.assertIn("<p>hello there</p>", build.md_to_html("hello there"))


class TestRenderBody(unittest.TestCase):
    """Math is stashed before the markdown pass and restored after, so KaTeX gets the
    source untouched. This is the documented gotcha the whole design exists for."""

    def test_inline_math_survives_verbatim(self):
        self.assertIn("$x^2$", build.render_body("value is $x^2$ here"))

    def test_display_math_survives_verbatim(self):
        self.assertIn("$$a + b$$", build.render_body("$$a + b$$"))

    def test_asterisks_inside_math_are_not_eaten_by_italic(self):
        """Without the stash, `* b *` inside math would become <em> and KaTeX would
        receive mangled input. This is the regression test for that."""
        self.assertIn("$a * b * c$", build.render_body("so $a * b * c$ holds"))

    def test_underscores_inside_math_survive(self):
        self.assertIn("$a_1$", build.render_body("term $a_1$ here"))

    def test_relative_image_gets_the_note_folder_prefix(self):
        out = build.render_body("![x](pic.png)", "leetcode")
        self.assertIn('src="leetcode/pic.png"', out)

    def test_http_image_is_left_alone(self):
        out = build.render_body("![x](https://e.com/pic.png)", "leetcode")
        self.assertIn('src="https://e.com/pic.png"', out)

    def test_absolute_image_is_left_alone(self):
        out = build.render_body("![x](/imgs/pic.png)", "leetcode")
        self.assertIn('src="/imgs/pic.png"', out)


class TestShortLabel(unittest.TestCase):
    def test_leetcode_uses_the_problem_number(self):
        self.assertEqual(build.short_label("leetcode", "84. Largest Rectangle"), "84")

    def test_leetcode_without_a_number_falls_back_to_title(self):
        self.assertEqual(build.short_label("leetcode", "Two Sum"), "Two Sum")

    def test_short_title_is_untouched(self):
        self.assertEqual(build.short_label("ai", "Transformers"), "Transformers")

    def test_long_title_is_truncated(self):
        out = build.short_label("ai", "A" * 40)
        self.assertTrue(out.endswith("…"))
        self.assertEqual(len(out), 16)


class TestStripNoteFront(unittest.TestCase):
    def test_starts_at_the_first_real_section(self):
        out = build.strip_note_front("# Title\n\n> Source: x\n\n## Real section\nbody")
        self.assertTrue(out.startswith("## Real section"))
        self.assertNotIn("Source:", out)

    def test_contents_block_is_skipped(self):
        out = build.strip_note_front("# Title\n\n## Contents\n- a\n\n## Real\nbody")
        self.assertTrue(out.startswith("## Real"))

    def test_falls_back_to_dash_split(self):
        out = build.strip_note_front("# Title\n---\nmeta\n---\nbody here")
        self.assertEqual(out, "body here")

    def test_falls_back_to_dropping_the_h1(self):
        self.assertEqual(build.strip_note_front("# Title\njust text"), "just text")


class TestResolveWikilinks(unittest.TestCase):
    def test_known_target_becomes_a_link(self):
        cards = [
            {"id": "os-deadlock", "body_html": "see [[os-deadlock]]"},
            {"id": "other", "body_html": ""},
        ]
        build.resolve_wikilinks(cards)
        self.assertIn('class="wl"', cards[0]["body_html"])

    def test_unknown_target_degrades_to_plain_text(self):
        """A dangling link must never leak raw `[[ ]]` onto the page."""
        cards = [{"id": "a", "body_html": "see [[os-nonexistent]]"}]
        build.resolve_wikilinks(cards)
        self.assertNotIn("[[", cards[0]["body_html"])
        self.assertIn("nonexistent", cards[0]["body_html"])


class TestVisibilitySafetyBelt(unittest.TestCase):
    """THE test. collect() renders only `visibility: public` files; anything else is
    skipped. This is what stops a private note that lands in the repo by accident from
    being published. ../CLAUDE.md: "SAFETY BELT ... Never bypass it."
    """

    def _collect_from(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "notes").mkdir()
            for name, text in files.items():
                (root / "notes" / name).write_text(text, encoding="utf-8")
            with mock.patch.object(build, "ROOT", root), \
                 mock.patch.object(build, "CONTENT_DIRS", ["notes"]), \
                 mock.patch.object(build, "external_ai_cards", lambda: []):
                return build.collect()

    @staticmethod
    def _note(note_id, visibility):
        return f"---\nid: {note_id}\ntitle: {note_id}\nvisibility: {visibility}\n---\nbody\n"

    def test_only_public_notes_are_collected(self):
        cards = self._collect_from({
            "pub.md": self._note("pub", "public"),
            "priv.md": self._note("priv", "private"),
        })
        self.assertEqual([c["id"] for c in cards], ["pub"])

    def test_missing_visibility_is_treated_as_private(self):
        """Fail closed: a note with no `visibility` key must not be published."""
        cards = self._collect_from({
            "no-key.md": "---\nid: no-key\ntitle: t\n---\nbody\n",
        })
        self.assertEqual(cards, [])

    def test_a_file_with_no_frontmatter_is_not_published(self):
        cards = self._collect_from({"raw.md": "# Just a heading\n\nsecrets\n"})
        self.assertEqual(cards, [])

    def test_visibility_must_match_exactly(self):
        """`public-ish`, `Public`, `draft` — none of these open the belt."""
        cards = self._collect_from({
            "a.md": self._note("a", "Public"),
            "b.md": self._note("b", "public-draft"),
        })
        self.assertEqual(cards, [])

    def test_readme_is_skipped(self):
        cards = self._collect_from({"README.md": self._note("readme", "public")})
        self.assertEqual(cards, [])


if __name__ == "__main__":
    unittest.main()
