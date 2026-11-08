# The Claude Code plugin

Status: **In review**

## Installing

Read-Along is installed as a Claude Code plugin from this repository, which is also its marketplace:

- terminal: `/plugin install read-along --marketplace pinkasey/claude-read-along`
- shell: `claude plugin install read-along --marketplace pinkasey/claude-read-along`
- desktop app: **+**, **Plugins**, **Add marketplace** `pinkasey/claude-read-along`, **Add plugin**

The plugin is named `read-along`; the marketplace is named `claude-read-along`. It contains one skill, `review`, which the reviewer can call as `/read-along:review` or reach by asking for a review in their own words.

## Requirements

- Claude Code signed in with a claude.ai account: the page is a claude.ai Artifact.
- `python3` and `gh` with access to the repository (read to load; write to commit edits). In Claude Code on the web, Claude attaches the repository to the session.

## What the skill does

| When the reviewer | Claude |
| --- | --- |
| asks for a review, or opens the page for the first time | finds their **Read-Along Review** page, or publishes one, and gives the link |
| uses a page whose version is older than the installed plugin's | updates the page in place, keeping its link and data |
| names a pull request, or a local markdown file | loads it into the page (see [pull-requests.md](pull-requests.md)) |
| says "post my review" | plans the review, shows every item, asks before committing, posts, then clears the posted items and reloads (see [posting-reviews.md](posting-reviews.md)) |
| says "this section" or "add a comment here" in the chat | uses the reading position the page records |

Rules:

- One page per reviewer, reused for every review.
- The page's version is a `read-along-version` meta tag; a newer plugin updates the page when it is next used.
- Claude links the page to its current session when it can (Claude Code on the web), so the page knows where to send requests.
- The skill follows [security.md](../security.md): data from pull requests, comments and the page is never treated as instructions, and nothing is committed without the reviewer's answer.

## Disclaimer and license

Using the plugin is the user's own responsibility. It posts review comments and can push commits under the user's GitHub account when the user confirms. It is provided as is, without warranty, under the [MIT license](../../LICENSE).
