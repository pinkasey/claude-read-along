#!/usr/bin/env python3
"""Repository checks run in CI.

  check_repo.py [--base REF]

- Page safety: every external script loads from an allowed CDN with an integrity hash; stylesheets
  only from Google Fonts.
- Page version: when the page changed since REF (the pull request's base), its read-along-version
  must go up, so installed plugins update pages that are already published.
- Docs links: relative links in markdown files point at files that exist.
"""
import argparse
from html.parser import HTMLParser
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PAGE = "page/read-along-review.html"
SCRIPT_HOSTS = ("https://cdnjs.cloudflare.com/", "https://cdn.jsdelivr.net/npm/", "https://unpkg.com/")


class Tags(HTMLParser):
    """Collects <script>, <link> and <meta> elements with their attributes, the way a browser reads
    them: case, quoting and spacing do not matter, and data-* attributes are not mistaken for others."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "link", "meta"):
            self.tags.append((tag, {k.lower(): (v or "") for k, v in attrs}))

    handle_startendtag = handle_starttag


def parse(html):
    p = Tags()
    p.feed(html)
    return p.tags


def page_version(html):
    for tag, a in parse(html):
        if tag == "meta" and a.get("name") == "read-along-version" and re.fullmatch(r"\d+\.\d+\.\d+", a.get("content", "")):
            return tuple(int(x) for x in a["content"].split("."))
    return None


def check_page(html):
    errors = []
    for tag, a in parse(html):
        if tag == "script" and "src" in a:
            src = a["src"].strip()
            if not src.startswith(SCRIPT_HOSTS):
                errors.append(f"script from a host that is not allowed: {src}")
            if not re.fullmatch(r"sha(256|384|512)-[A-Za-z0-9+/=]+", a.get("integrity", "").strip()):
                errors.append(f"script without an integrity hash: {src}")
            if a.get("crossorigin", "").strip().lower() != "anonymous":
                errors.append(f'script without crossorigin="anonymous": {src}')
        if tag == "link" and "stylesheet" in a.get("rel", "").lower().split():
            if not a.get("href", "").strip().startswith("https://fonts.googleapis.com/"):
                errors.append(f"stylesheet from a host that is not allowed: {a.get('href')}")
    if not page_version(html):
        errors.append('the page has no <meta name="read-along-version" content="X.Y.Z">')
    return errors


def check_version(base, html):
    old = subprocess.run(["git", "-C", ROOT, "show", f"{base}:{PAGE}"], capture_output=True, text=True)
    if old.returncode != 0:
        return []  # the page is new on this branch, or the base is unknown
    if old.stdout == html:
        return []
    was, now = page_version(old.stdout), page_version(html)
    if was and now and now <= was:
        fmt = lambda v: ".".join(map(str, v))
        return [f"{PAGE} changed but read-along-version went from {fmt(was)} to {fmt(now)}: it must go up, "
                "or installed plugins never update pages that are already published"]
    return []


def check_links():
    errors = []
    files = subprocess.run(["git", "-C", ROOT, "ls-files", "*.md"], capture_output=True, text=True, check=True).stdout.split()
    for rel in files:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            text = fh.read()
        text = re.sub(r"```.*?```", "", text, flags=re.S)  # links inside code blocks are examples
        for target in re.findall(r"\]\(([^)\s]+)\)", text):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
                continue
            path = target.split("#")[0]
            if path and not os.path.exists(os.path.normpath(os.path.join(ROOT, os.path.dirname(rel), path))):
                errors.append(f"{rel}: broken link to {target}")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", help="git ref the branch will merge into, for the page version check")
    a = ap.parse_args()
    with open(os.path.join(ROOT, PAGE), encoding="utf-8") as fh:
        html = fh.read()
    errors = check_page(html) + check_links()
    if a.base:
        errors += check_version(a.base, html)
    for e in errors:
        print("ERROR: " + e)
    print(f"{len(errors)} problem(s)" if errors else "All repository checks passed.")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
