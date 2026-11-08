# claude-read-along

Code-review markdown files with Claude, by listening. A review page reads the document aloud section by section, highlights the sentence being spoken, and lets you jump, take notes and make edits, by clicking, by keyboard or by dictated voice commands. Notes and edits stay with the page until you ask Claude to post them to the pull request.

It works with a pull request (changed sections, existing review comments, several files) and with plain markdown files.

## What's here

| Path | What it is |
| --- | --- |
| `page/read-along-review.html` | The review page, published by Claude as a private claude.ai page. Reading uses the browser's built-in speech. |
| `tools/pr_loader.py` | Fetches a pull request's markdown files, changed lines and review comments with `gh`, and writes them as JSON documents for the page's database. Also loads plain local files. |
| `examples/sample-design-doc.md` | A sample design document to try it on. |

## How a review goes

1. In a Claude Code session, ask Claude to load a pull request (`owner/repo` and number) or a markdown file into the review page.
2. Open the page. Press play, or click any section.
3. Take notes and make edits as you listen. Claude can read them back at any time.
4. Tell Claude "post my review". Claude shows what it will post and posts only after you confirm.

## Page features

- Section-by-section reading with sentence highlighting and auto-scroll; click a section to read from there.
- Outline of headings; chapters with pull-request changes are marked, with counts of review comments.
- Pull requests: changed sections are marked and announced ("Changed."), a **Changed only** mode skips the rest, and existing review comments are read after their section (bot comments are shown but not read).
- Notes and edits per file; edits can be proposed by voice ("change 2,000 to 3,000", "edit make this shorter").
- Voice commands, dictated with the operating system's own dictation (Win+H on Windows, the keyboard microphone on phones), typed into the command box: play, pause, next, back, repeat, faster, slower, next chapter, next change, next comment, next file, go to line N, add note …, undo.
- Speed 0.8× to 3×, voice choice, keep-screen-on.

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
