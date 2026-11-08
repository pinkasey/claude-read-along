# Reading

Status: **Shipped**

## Sections

The document is split into reading sections, each read as one unit:

- each heading,
- each paragraph,
- each list item, nested items included (a nested item is its own section, indented under its parent),
- each table, code block and quote as a whole,
- the front matter (a `---` block at the very start of the file),
- each block of `<!-- comments -->` on its own lines.

Horizontal rules, blank lines and link definitions are not sections.

### Front matter and comments

GitHub hides front matter (it shows it as a small table) and `<!-- comments -->` (it does not show them at all). The page shows both, so the reviewer sees what the file really says (**Shipped**, [#11](https://github.com/pinkasey/claude-read-along/pull/11)):

- Front matter is shown as it is written, in a dashed box labeled "Front matter". It is never read as a heading or paragraph.
- A comment block is shown in a dashed box labeled "Comment", with the comment's text.
- A comment inside a paragraph or list item is shown in place, as dimmed text between `<!--` and `-->`.
- Comments inside code blocks are code, and stay as they are.
- The text of a comment is shown as text: markup inside it is never rendered.

Every section shows its starting line number from the file in a gutter, so comments can point at real lines.

## What is read aloud

| Section | Spoken as |
| --- | --- |
| Heading, paragraph, quote | Its text, without markdown symbols. A quote starts with "Quote." |
| List item | Its text. A task item starts with "Done:" or "To do:". |
| Table | "Table with N rows", then each row: "Row 1. Column: value. …" |
| Code block | "Code block in LANGUAGE, N lines." With **Read code** on, each line is then read. |
| Front matter | "Front matter, N lines." With **Read hidden** on, each line is then read. |
| Comment block | "Hidden comment." With **Read hidden** on, its text is then read. |

Text is spoken one sentence at a time, and long sentences are split at commas or spaces into chunks of about 200 characters. This keeps playback responsive and avoids browsers cutting off long utterances.

A section that has an edit is read as edited.

Comments inside a paragraph or list item are skipped, and with **Read hidden** on they are read where they appear.

## Highlighting and scrolling

- The section being read has a highlight and a marker on its left edge, and is scrolled to the middle of the screen.
- Inside headings, paragraphs, list items and quotes, the sentence being spoken has a stronger highlight. Browsers without the CSS Custom Highlight API keep the section highlight only.
- The header (title, pull request, file picker, counts and buttons) stays at the top while scrolling, so switching files is always one click away. On a phone it is compact: one line each for the title and the pull request, the file picker, and one row of counts and buttons that scrolls sideways.
- Each panel has a chevron in its corner that folds it to a single line: the top panel to the document title, the bottom panel to what is being read and the play, previous, next and repeat buttons. The chevron unfolds it again, and the page remembers each panel's state.
- The player bar shows the current line, the position (for example 7/42), the section's first words, and a progress bar.

## Navigation

| Action | Mouse or touch | Keyboard | Voice |
| --- | --- | --- | --- |
| Play / pause | Play button | Space or K | play, pause, stop |
| Next / previous sentence | | → / ← | next sentence, previous sentence |
| Next / previous section | Arrow buttons | ↓ or J / ↑ or H | next, back |
| Repeat the section | Repeat button | R | repeat |
| Read from a section | Click or tap it | | go to line N |
| Next / previous chapter | Outline | | next chapter, previous chapter, start of chapter |

Rules:

- Clicking a section starts reading there.
- Moving by sentence crosses into the neighbouring section at a section's edge. While reading, it reads on from the new sentence; while paused, it highlights that sentence, and play starts from it.
- With **Continuous** on (the default), reading moves to the next section by itself, with a slightly longer pause after headings. With it off, reading stops after each section.
- Pausing keeps the sentence position; play resumes from that sentence.
- Loading another document or switching files starts from the first section and sentence.
- Keyboard shortcuts do not fire while typing in a field. Space and Enter on a focused button press that button, and Space on a focused checkbox ticks it; the arrow keys keep working after ticking one.

## Outline

The right-hand panel (the **Review list** button on narrow screens) starts with an outline of the headings, indented by level. Clicking a heading reads from there. The chapter being read is highlighted. In a pull request, a dot marks chapters with changes, and a number counts their review comments.

## Settings

| Setting | Default | Notes |
| --- | --- | --- |
| Speed | 1× | 0.8× to 3×. Changing it while reading restarts the current sentence at the new speed. |
| Voice | Browser default | Voices in the browser's language are listed first. |
| Continuous | On | |
| Read code | Off | |
| Read hidden | Off | Reads front matter and `<!-- comments -->` instead of only announcing them. |
| Screen on | On | Asks the browser to keep the screen awake while reading. |

Speed, voice and the toggles are remembered in the browser.

On a phone, these settings fold behind a **Settings** button next to **Comment** and **Edit**, so the player takes less room from the text; the button opens and closes them, and the page remembers which.

## When speech is not available

If the browser cannot speak, pressing play says so. Everything else (reading on screen, comments, edits) still works.
