# Notes and edits

Status: **In review**

## What they are

- A **note** is a review comment on a section: text the reviewer wants the author to read.
- An **edit** is the reviewer's own replacement for a section's markdown.

Both stay on the page until the reviewer asks Claude to post them (see [posting-reviews.md](posting-reviews.md)).

## Making them

| How | Note | Edit |
| --- | --- | --- |
| Button or key | **Note** (N) opens a box under the current section | **Edit** (E) opens the section's markdown for editing |
| Voice | "add note TEXT" saves at once | "change X to Y" or "edit INSTRUCTION" proposes an edit to accept or cancel |

Opening a box pauses reading. Saving an edit whose text is unchanged removes any existing edit instead.

## What the reviewer sees

- Notes appear under their section, labelled **Note**.
- An edited section shows its new text with an **edited** label, and is read aloud as edited.
- The **Review, not yet posted** list in the right-hand panel lists every note and edit of the current file in line order, each with **Go to** and **Delete** (or **Undo edit**). An edit shows the old text struck through and the new text.
- The header counts the file's notes and edits.

## Rules

- A note or edit is attached to its section by the section's starting line and records the section's line range, the file and the pull request (its **scope**).
- Notes and edits are shown, read and posted only within their own scope: one file of one pull request, or one loaded document. Loading or pasting another document never shows earlier notes or edits.
- An edit has an id derived from a hash of its full scope and its section, so two files never share an edit id.
- Each section has at most one edit; editing again replaces it.
- Text typed into a note or edit box survives the page redrawing (for example when other data arrives) until it is saved or cancelled.
- **Undo** (voice) removes the most recent note or edit made by voice, in the file it was made in, even after switching files.

## Where they are kept

| Page opened | Kept in | Visible to |
| --- | --- | --- |
| In claude.ai (normal use) | The page's shared database | People the page is shared with, and Claude when reading them back |
| As a plain file, outside claude.ai | The browser's local storage | That browser only |

While notes and edits are kept in the database, the header says "Saved for Claude · not posted".
