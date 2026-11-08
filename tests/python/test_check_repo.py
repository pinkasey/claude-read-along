"""Tests for tools/ci/check_repo.py: the page safety and page version checks."""
import importlib.util
import os
import types
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
spec = importlib.util.spec_from_file_location("check_repo", os.path.join(ROOT, "tools", "ci", "check_repo.py"))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

GOOD_SCRIPT = '<script src="https://cdnjs.cloudflare.com/x.js" integrity="sha512-AAAA" crossorigin="anonymous"></script>'
VERSION = '<meta name="read-along-version" content="{}">'


def page(*parts, version="0.1.0"):
    return VERSION.format(version) + "".join(parts)


class PageSafety(unittest.TestCase):
    def test_a_safe_page_passes(self):
        self.assertEqual(check.check_page(page(GOOD_SCRIPT, '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?x">')), [])

    def test_formatting_does_not_hide_a_script(self):
        for tag in (
            '<SCRIPT SRC="https://example.invalid/x.js"></SCRIPT>',
            '<script src = "https://example.invalid/x.js"></script>',
            "<script src='https://example.invalid/x.js'></script>",
            "<script src=https://example.invalid/x.js></script>",
        ):
            errors = check.check_page(page(tag))
            self.assertTrue(any("not allowed" in e for e in errors), tag)
            self.assertTrue(any("integrity" in e for e in errors), tag)

    def test_data_attributes_are_not_the_real_ones(self):
        tag = '<script src="https://cdnjs.cloudflare.com/x.js" data-integrity="sha512-AAAA" data-crossorigin="anonymous"></script>'
        errors = check.check_page(page(tag))
        self.assertTrue(any("integrity" in e for e in errors))
        self.assertTrue(any("crossorigin" in e for e in errors))

    def test_duplicate_attributes_cannot_hide_the_real_one(self):
        # A browser uses the first of a repeated attribute.
        script = ('<script src="https://example.invalid/x.js" src="https://cdnjs.cloudflare.com/x.js" '
                  'integrity="" integrity="sha512-AAAA" crossorigin="anonymous"></script>')
        errors = check.check_page(page(script))
        self.assertTrue(any("repeats attribute" in e for e in errors))
        self.assertTrue(any("not allowed" in e and "example.invalid" in e for e in errors), errors)
        self.assertTrue(any("integrity" in e and "repeats" not in e for e in errors), errors)
        link = '<link rel="stylesheet" href="https://evil.example/x.css" href="https://fonts.googleapis.com/css2">'
        errors = check.check_page(page(link))
        self.assertTrue(any("repeats attribute" in e for e in errors))
        self.assertTrue(any("evil.example" in e for e in errors), errors)

    def test_stylesheets_only_from_google_fonts(self):
        for tag in ("<link rel='stylesheet' href='https://evil.example/x.css'>", '<LINK REL="Stylesheet" HREF="https://evil.example/x.css">'):
            self.assertTrue(any("stylesheet" in e for e in check.check_page(page(tag))), tag)

    def test_version_is_required(self):
        self.assertTrue(any("read-along-version" in e for e in check.check_page(GOOD_SCRIPT)))


class PageVersion(unittest.TestCase):
    def setUp(self):
        self.saved = check.subprocess.run

    def tearDown(self):
        check.subprocess.run = self.saved

    def versions(self, old, new, same_page=False):
        old_html = page("<p>old</p>", version=old)
        check.subprocess.run = lambda *a, **k: types.SimpleNamespace(returncode=0, stdout=old_html)
        return check.check_version("origin/main", old_html if same_page else page("<p>new</p>", version=new))

    def test_must_go_up(self):
        self.assertEqual(self.versions("0.1.3", "0.1.4"), [])
        self.assertEqual(self.versions("0.1.9", "0.1.10"), [], "compared as numbers, not text")
        self.assertEqual(self.versions("0.9.9", "1.0.0"), [])

    def test_unchanged_or_lower_fails(self):
        self.assertTrue(self.versions("0.1.3", "0.1.3"))
        self.assertTrue(self.versions("0.1.3", "0.1.2"))
        self.assertTrue(self.versions("0.1.10", "0.1.9"))

    def test_an_unchanged_page_needs_no_new_version(self):
        self.assertEqual(self.versions("0.1.3", "0.1.3", same_page=True), [])


if __name__ == "__main__":
    unittest.main()
