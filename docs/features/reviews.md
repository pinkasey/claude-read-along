# Switching between reviews

Status: **Shipped** ([#13](https://github.com/pinkasey/claude-read-along/pull/13))

A reviewer often works on several pull requests at once, each in its own Claude session. The page keeps every review that was loaded into it, so switching between them is instant and needs no Claude.

## Kept reviews

- Every pull request, repository folder or file set Claude loads is kept as a review on the page. Loading one that is already there replaces it, so each appears once.
- Loading a review shows it. Reviews loaded earlier stay, with their files, until removed.
- The page keeps up to 15 reviews. When Claude loads a 16th, it removes the ones loaded longest ago that have no unposted comments or edits, and says which.
- Unposted comments and edits belong to their review (they are scoped to it, see [comments-and-edits.md](comments-and-edits.md)), so switching never mixes them, and none is listed under **Other documents** while its review is kept.

## Switching

- With two or more reviews, a picker under the title lists them, most recently opened first, each with when it was loaded and how many unposted comments and edits it has. Choosing one shows it at once.
- The last entry, **Open another, reload or remove…**, opens the Open panel.
- The page remembers the reviewer's place in each review (in this browser), and returns to it when switching back.
- The shown review is saved, so Claude knows which review "this section" and "post my review" refer to.

## The Open panel

- It lists **Your reviews**, with **Open** and (for the page's owner) **Remove** on each.
- Typing a pull request or repository that is already loaded changes the button to **Switch to it**, which switches without Claude. Typing the review being read changes it to **Ask Claude to reload it**, for its latest commits. Anything else is **Ask Claude to load it**, as before.
- **Remove** asks first, then removes the review and its files. Its unposted comments and edits are kept, under **Other documents**, where they can be deleted.

## Sessions

- Each review remembers the Claude session that loaded it. **Open PR or repo** and **Post review** send their requests about a review to that session, else to the page's linked session ([page-and-sessions.md](page-and-sessions.md)). Each panel still shows the sentence to paste into a chat.
- When a Claude session with the plugin opens or starts working on a pull request that changes markdown, and the user has a Read-Along page, Claude loads that pull request into the page without being asked, and says so in one line. Moving to another session's work then needs no prompt: its pull request is already on the page.

## Freshness

The page cannot see new commits by itself. Each review shows when it was loaded; reloading it (from the Open panel) asks Claude for the latest.
