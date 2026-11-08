# Posting reviews

Status: **In review**

## Starting

The reviewer either presses **Post review** in the page and then **Ask Claude to post**, or tells Claude "post my review". Posting works for pull requests only; for a plain file, the reviewer asks Claude to apply the edits to the file.

## The two settings

GitHub accepts review comments only on lines inside the pull request's diff (changed lines and the unchanged lines shown around them). Two settings decide what happens to everything else.

| Setting | Built-in default | Alternative |
| --- | --- | --- |
| **Edits on changed lines** | **Suggest edits**: review comments with suggested changes, which the author applies with one click | **Commit inline**: Claude commits the edits to the pull request's branch |
| **Notes and edits on unchanged lines** | **List in the summary**: nothing is committed; they go in the review summary with their line numbers | **Commit and comment**: Claude commits a marker for a note, or the edited text for an edit, and comments on it |

- Each person's choice is saved as their own default, privately, and follows them across devices. Without a saved choice, the built-in defaults apply.
- The **Post review** panel shows the settings, and the plan: how many notes and edits go where.

## What happens to each item

| Item | Where | Result |
| --- | --- | --- |
| Note | Inside the diff | A review comment on its line |
| Note | Outside the diff, **List in the summary** | Listed in the review summary with its file, line and the section's first words |
| Note | Outside the diff, **Commit and comment** | A `<!-- review note -->` line is committed right after the section (indented to stay inside a list item), and the note is posted as a comment on that line. The comment ends with a short explanation and an empty suggested change, so the author removes the marker with one click (**Commit suggestion**). The page does not read the explanation aloud. |
| Edit | Inside the diff, **Suggest edits** | A suggested change replacing the section's lines |
| Edit | Inside the diff, **Commit inline** | Committed to the branch; listed under "Committed during review" in the summary |
| Edit | Outside the diff, **List in the summary** | Listed in the summary with the suggested text |
| Edit | Outside the diff, **Commit and comment** | Committed, with a comment on the new lines that says so and offers a one-click revert: "_To **REVERT** this change, press **Commit suggestion** below._", followed by a suggested change that restores the original lines |
| Edit whose original text is no longer at its line | Anywhere | Listed in the summary, with the reason |

Everything goes into one review (state "comment"; never "approve" or "request changes"), whose summary lists the commits made and the items not posted as line comments.

## Confirmation

- Before posting, Claude shows the plan: how many comments, suggestions and commits, on which branch, and every item with its file, line and text.
- When the plan commits anything, Claude asks first: "Commit X edits as Y lines to BRANCH? Alternatively, post them as comments with suggested edits." with the choices **Commit inline** and **Suggest edits**. Nothing is committed without that answer, even when the request came from the page.

## Safety

- If the pull request has new commits since it was loaded, Claude warns that line numbers may have moved, and asks the reviewer to reload and check before posting.
- Commits are made against the exact version that was planned. If a file changed in between, GitHub refuses the commit, and nothing is posted.
- All committed items go into one commit, made in a separate git worktree of the session's clone on top of the planned head and pushed as a fast-forward, never forced. Without a clone, the script uses GitHub's contents API instead (one commit per file), where the environment allows it.
- After committing, Claude checks that every comment still lands inside the diff; any that do not move to the summary.
- Pull requests from forks cannot be committed to. Their commit items become suggestions or summary entries, and Claude says so.
- Suggestions and quoted text are fenced so that code blocks inside them stay intact.
- Only markdown files the pull request adds or changes can be commented on or committed to; an item naming any other file is skipped with a warning. See [security.md](../security.md).

## After posting

Claude reports the review's link and the commits, removes the posted notes and edits from the page, and reloads the pull request, so the posted comments appear as review comments.
