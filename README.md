# claude-read-along

Code-review markdown files with Claude, by listening. A review page reads the document aloud section by section, highlights the sentence being spoken, and lets you jump, take notes and make edits, by clicking, by keyboard or by dictated voice commands. Notes and edits stay with the page until you ask Claude to post them to the pull request.

It works with a pull request (changed sections, existing review comments, several files) and with plain markdown files.

## What's here

| Path | What it is |
| --- | --- |
| `page/read-along-review.html` | The review page, published by Claude as a private claude.ai page. Reading uses the browser's built-in speech. |
| `tools/pr_loader.py` | Fetches a pull request's markdown files, changed lines and review comments with `gh`, and writes them as JSON documents for the page's database. Also loads plain local files. |
| `tools/post_review.py` | Posts a review to its pull request in two steps: `plan` (changes nothing) and `execute`. |
| `examples/sample-design-doc.md` | A sample design document to try it on. |
| `docs/` | How Read-Along behaves: the product overview and one document per feature area. Start at [docs/README.md](docs/README.md). |

## Getting to the page

The review page is a private claude.ai page (an Artifact) that belongs to you. Claude publishes it the first time you ask for a review in Claude Code (web, desktop app or terminal), and it then stays at the same link. To open it again without asking Claude:

- use the link Claude gave you,
- find it in your artifacts at claude.ai/code/artifacts (in the terminal, `/artifacts`),
- or pin it to your claude.ai sidebar (ask Claude to pin the review page).

In the Claude Code app the page can sit in the side pane, next to the chat.

## What works on the page alone, and what needs Claude

| On the page alone | Needs a Claude Code session |
| --- | --- |
| Listening, navigation, voice commands | Loading a pull request (the page cannot reach GitHub) |
| Notes and edits | Posting the review, and committing edits |
| Opening or pasting a local markdown file | |
| Edits proposed by voice ("edit make this shorter"), which ask Claude directly from the page | |

The page's **Open pull request** and **Post review** buttons send the request to the Claude Code session that last loaded the page. If that session has ended, the panel shows the sentence to paste into a new session instead.

## How a review goes

1. Load a pull request: press **Open pull request** in the page, or tell Claude in the chat which pull request to review.
2. Press play, or click any section.
3. Take notes and make edits as you listen. Claude can read them back at any time.
4. Press **Post review** in the page, or tell Claude "post my review". Claude shows what it will post and commit, and acts only after you confirm.

## Installation

Packaging as a Claude Code plugin is the next step, and installation instructions come with it. Until then, the tool runs from a Claude Code session that has this repository: ask Claude to publish `page/read-along-review.html` as a private page and to load a pull request with `tools/pr_loader.py`.

## Page features

- Section-by-section reading with sentence highlighting and auto-scroll; click a section to read from there.
- Outline of headings; chapters with pull-request changes are marked, with counts of review comments.
- Pull requests: changed sections are marked and announced ("Changed."), a **Changed only** mode skips the rest, and existing review comments are read after their section (bot comments are shown but not read).
- Notes and edits per file; edits can be proposed by voice ("change 2,000 to 3,000", "edit make this shorter").
- Voice commands, dictated with the operating system's own dictation (Win+H on Windows, the keyboard microphone on phones), typed into the command box: play, pause, next, back, repeat, faster, slower, next chapter, next change, next comment, next file, go to line N, add note …, undo.
- Speed 0.8× to 3×, voice choice, keep-screen-on.

## Posting a review

GitHub only accepts review comments on lines inside the pull request's diff. Two settings decide what happens, chosen in the page's **Post review** panel and saved per person:

| Setting | Default | Alternative |
| --- | --- | --- |
| Edits on changed lines | Suggested changes the author applies with one click | Committed to the pull request branch |
| Notes and edits on unchanged lines | Listed in the review summary with line numbers | Committed (a `<!-- review note -->` marker for a note, the edited text for an edit), with a review comment on it |

Claude always asks before committing anything. Pull requests from forks cannot be committed to, so those items fall back to suggestions or the summary.

```bash
python3 tools/post_review.py plan --pr OWNER/REPO NUMBER --data EXPORT_DIR --edit-mode suggest --outside summary --out plan.json
```

```bash
python3 tools/post_review.py execute --plan plan.json --out result.json --repo-dir path/to/clone
```

## Commands for the loader

```bash
python3 tools/pr_loader.py pr OWNER/REPO NUMBER OUT_DIR
```

```bash
python3 tools/pr_loader.py local OUT_DIR path/to/file.md [more.md]
```

## Known limits

- The page cannot use the microphone itself inside claude.ai, so voice commands rely on the operating system's dictation into the command box.
- Speech usually stops when a phone's screen locks; the page keeps the screen awake while reading.
