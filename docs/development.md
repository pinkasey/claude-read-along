# Development: tests and CI

Every pull request runs three CI jobs (`.github/workflows/ci.yml`). All must pass before merging.

| Job | What it checks | Run it locally |
| --- | --- | --- |
| **Python tests** | `tools/pr_loader.py` and `tools/post_review.py`: diff parsing, applying edits and markers, line mapping after commits, code fences, revert and removal suggestions, the posting plan in every mode, the path allowlist against forged items, forks, what gets posted, and committing with git against a local stand-in for GitHub | `python3 -m unittest discover -s tests/python -v` |
| **Page tests** | The page in headless Chromium, with stand-ins for speech, the page database, the viewer, the Claude Code connector, permissions and "ask Claude": reading and highlighting, sentence and section navigation, the sticky header, focus in voice mode, voice commands, comments and edits, pull request features, the panels and settings, sending to Claude in each failure case, untrusted markdown, view-only visitors, leftover items, old documents | `npm install`, then `npm run test:page` |
| **Plugin and repository checks** | `claude plugin validate .`; every external script from an allowed CDN with an integrity hash (read with an HTML parser, so case, quoting and spacing cannot hide one); the page version raised (strictly higher) whenever the page changes; relative links in markdown files | `python3 tools/ci/check_repo.py --base origin/main`, and `claude plugin validate .` |

The page tests load `marked` and `DOMPurify` from cdnjs, so they need network access.

## Rules for changes

- A change in behavior comes with a test that fails without it, and with the matching update in `docs/` (see [docs/README.md](README.md)).
- A change to `page/read-along-review.html` raises its `read-along-version` (the check enforces it), so the skill updates pages people have already published.
- CI cannot check real speech, the real claude.ai page, or posting to GitHub. Try those by hand before merging a change that touches them.

## Layout

| Path | What it holds |
| --- | --- |
| `tests/python/test_tools.py` | Unit tests for the scripts |
| `tests/python/test_check_repo.py` | Tests for the repository checks |
| `tests/page/harness.js` | Opens the page with the stand-ins; `prFixture()` is a pull request with two files and review comments |
| `tests/page/*.test.js` | Page tests, one file per area (reading, voice and edits, pull requests, panels, security) |
| `tools/ci/check_repo.py` | The repository checks |
