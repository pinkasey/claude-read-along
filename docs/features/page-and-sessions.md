# The page and Claude sessions

Status: **In review**, except where marked **Planned**

## Where the page lives

- The review page is a private claude.ai page (an Artifact) owned by the reviewer. Claude publishes it the first time the reviewer asks for a review, and it keeps the same link afterwards.
- The reviewer reopens it from the link, from their artifacts at claude.ai/code/artifacts (`/artifacts` in the terminal), or from their claude.ai sidebar when pinned.
- In the Claude Code app, it can sit in the side pane next to the chat.
- Other people can open it only if the reviewer shares it from the page's Share menu.

## What needs Claude

| On the page alone | Needs a Claude Code session |
| --- | --- |
| Listening, navigation, voice commands | Loading a pull request |
| Notes and edits | Posting a review, committing |
| Opening or pasting a local markdown file | |
| Edits proposed by voice (the page asks Claude directly, with the reviewer's permission) | |

## How the page asks Claude

- When Claude loads the page, it records its session in the page's database.
- **Open pull request** and **Post review** send the request to that session as a message, through the Claude Code connector. The first time, claude.ai asks the reviewer to allow it.
- If the page cannot send (no recorded session, the connector is unavailable or not allowed, the session has ended), the panel says so. Each panel always shows the sentence to paste into a chat instead, with a **Copy** button.
- A request from the page never skips a confirmation: anything that commits still asks the reviewer in the chat.

## How Claude knows what "this section" means

While reading, the page records the current file, line and section in its database, so the reviewer can say in the chat "make a note here" or "what did we just read?".

## Stored data

| Data | Written by | Read by |
| --- | --- | --- |
| The document set: title, pull request, list of files | Claude | Page |
| Each file: markdown, changed lines, diff ranges, review comments | Claude | Page |
| Notes and edits | Page | Page, Claude (to post) |
| Current reading position | Page | Claude |
| The session to send requests to | Claude | Page |
| Each person's review settings (private to them) | Page | Page, Claude |
| Speed, voice, toggles, chosen file | Page | Page (browser storage only) |

## Planned

- **Packaging as a Claude Code plugin**, so any reviewer can install it and get their own page.
- **Starting a session from the page**: when no Claude session is available, the page starts one to load or post. This depends on the platform allowing pages to start sessions.
