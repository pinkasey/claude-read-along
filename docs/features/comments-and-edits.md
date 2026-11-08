# Comments and edits

Status: **Shipped**

## What they are

- A **comment** is the reviewer's review comment on a section: text the reviewer wants the author to read. On the page it is labelled **Your comment**, to tell it apart from the pull request's existing review comments.
- An **edit** is the reviewer's own replacement for a section's markdown.

Both stay on the page, unposted, until the reviewer asks Claude to post them (see [posting-reviews.md](posting-reviews.md)).

## Making them

| How | Comment | Edit |
| --- | --- | --- |
| Button or key | **Comment** (C, or N) opens a box under the current section | **Edit** (E) opens the section's markdown for editing |
| Voice | "add comment TEXT" saves at once ("add note TEXT" works too) | "change X to Y" or "edit INSTRUCTION" proposes an edit to accept or cancel |

Opening a box pauses reading. Saving an edit whose text is unchanged removes any existing edit instead.

## What the reviewer sees

- Their comments appear under their section, labelled **Your comment**.
- An edited section shows its new text with an **edited** label, and is read aloud as edited.
- The **Review, not yet posted** list in the right-hand panel lists every comment and edit of the current file in line order, each with **Go to** and **Delete** (or **Undo edit**). An edit shows the old text struck through and the new text.
- The header counts the file's comments and edits.

## Rules

- A comment or edit is attached to its section by the section's starting line and records the section's line range, the file and the pull request (its **scope**).
- Comments and edits are shown, read and posted only within their own scope: one file of one pull request, or one loaded document. Loading or pasting another document never shows earlier comments or edits.
- An edit has an id derived from a hash of its full scope and its section, so two files never share an edit id.
- Each section has at most one edit; editing again replaces it.
- Text typed into a comment or edit box survives the page redrawing (for example when other data arrives) until it is saved or cancelled.
- **Undo** (voice) removes the most recent comment or edit made by voice, in the file it was made in, even after switching files.
- Nothing stays hidden: comments and edits whose scope matches no loaded document (an earlier pull request, a pasted document, or items saved before scopes existed) are listed under **Other documents** in the right-hand panel, with where they came from, their text, **Delete** on each, and **Delete all** (a second press confirms). They are not shown in the document or posted. After loading a pull request, Claude reports such items and offers to delete them.
- A single document saved before documents had an identity gets one when its owner opens it, and its scope-less comments and edits move to it.

## Where they are kept

| Page opened | Kept in | Visible to |
| --- | --- | --- |
| In claude.ai (normal use) | The page's shared database; only the page's owner can write it | People the page is shared with, and Claude when reading them back |
| As a plain file, outside claude.ai | The browser's local storage | That browser only |

While comments and edits are kept in the database, the header says "Saved for Claude · not posted". (The database collection that holds comments is named `notes`, from before they were renamed; it is not shown anywhere.)
