# The page and Claude sessions

Status: **Shipped**, except where marked otherwise

## Where the page lives

- The review page is a private claude.ai page (an Artifact) owned by the reviewer. Claude publishes it the first time the reviewer asks for a review, and it keeps the same link afterwards.
- The reviewer reopens it from the link, from their artifacts at claude.ai/code/artifacts (`/artifacts` in the terminal), or from their claude.ai sidebar when pinned.
- In the Claude Code app, it can sit in the side pane next to the chat.
- Other people can open it only if the reviewer shares it from the page's Share menu. They see it as **View only**: only the owner can load documents, add comments and edits, or post. See [security.md](../security.md).

## What needs Claude

| On the page alone | Needs a Claude Code session |
| --- | --- |
| Listening, navigation, voice commands | Loading a pull request |
| Comments and edits | Posting a review, committing |
| Opening or pasting a local markdown file | |
| Edits proposed by voice (the page asks Claude directly, with the reviewer's permission) | |

## How the page asks Claude

- When Claude loads a review, it records its session with that review, and as the page's linked session. Requests about a review go to the session that loaded it, or to the linked session when the review has none (see [reviews.md](reviews.md)).
- **Open PR or repo** and **Post review** post the request as a comment on the page and send it to Claude (claude.ai's "Send to Claude" for comments), which wakes the Claude sessions watching the page (**Shipped**, [#15](https://github.com/pinkasey/claude-read-along/pull/15)). Claude watches the page whenever it loads a review into it.
  - The request names the session of the review it is about ("For Claude session …"); only that session acts on it, and replies in the comment's thread. Without a named session, any watching session acts.
  - claude.ai asks the reviewer once for permission to comment from the page. Only the page's editors can send to Claude.
  - If no Claude session is watching the page, the panel says so and the button is off.
- When the comment route is not available, the page falls back to sending a message through the Claude Code connector. **Known issue:** claude.ai refuses that call ("connector access isn't confirmed for this artifact"), so in practice the copy-into-chat route below is the fallback that works.
- Before sending through the connector, the page checks the reviewer's permission for the connector and, if it has not been given yet, asks for it with claude.ai's permission dialog. If the reviewer declined, the panel offers **Open permissions** (claude.ai's Permissions panel) to turn it back on.
- When a panel opens, the page checks whether it can message Claude for this person (a linked session, the connector, its send tool) and says so at once if not.
- If sending fails, the panel shows the reason and the connector's details. For failures that can be retried, the button changes to **Try again**; the page never retries by itself, because a failed send may still have arrived.
- If the page cannot send (no recorded session, the connector is unavailable or not allowed, the session has ended), the panel says so. Each panel always shows the sentence to paste into a chat instead, with a **Copy** button.
- A request from the page never skips a confirmation: anything that commits still asks the reviewer in the chat.

## How Claude knows what "this section" means

While reading, the page records the current file, line and section in its database, so the reviewer can say in the chat "add a comment here" or "what did we just read?".

## Stored data

| Data | Written by | Read by |
| --- | --- | --- |
| Every loaded review: title, pull request or repository, list of files, when it was loaded, the session that loaded it | Claude | Page |
| Which review is shown | Claude (on loading), page (on switching) | Page, Claude |
| Each file: markdown, changed lines, diff ranges, review comments | Claude | Page |
| Comments and edits | Page | Page, Claude (to post) |
| Current reading position | Page | Claude |
| The session to send requests to | Claude | Page |
| Each person's review settings (private to them) | Page | Page, Claude |
| Speed, voice, toggles, chosen file, the place in each review | Page | Page (browser storage only) |

## Planned

- **Starting a session from the page**: when no Claude session is available, the page starts one to load or post. This depends on the platform allowing pages to start sessions.
