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

## How a review goes

1. Open a pull request from the page (**Open pull request**), or ask Claude in the chat to load a pull request or a markdown file.
2. Open the page. Press play, or click any section.
3. Take notes and make edits as you listen. Claude can read them back at any time.
4. Press **Post review** in the page, or tell Claude "post my review". Claude shows what it will post and commit, and acts only after you confirm.

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
python3 tools/post_review.py execute --plan plan.json --out result.json
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
