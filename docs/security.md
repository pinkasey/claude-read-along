# Security and privacy

Status: **Shipped**

Read-Along handles text written by other people (pull request markdown and review comments), and it can post and commit under the reviewer's GitHub account. These are the rules that keep that safe. A change that weakens one of them needs a reason in its pull request.

## Who can change what

- Only the page's owner can write its shared data: loaded documents, comments, edits, the reading position, and the session the page sends requests to. Anyone the page is shared with can read it.
- Each person can write only their own review settings, which nobody else can read.
- A person viewing someone else's page sees "View only": comment, edit, load and post controls are off.
- Only the owner can switch the page's shown review or remove a review. A viewer can switch reviews for themselves; that changes nothing stored.
- Each review's recorded session is written by Claude, like the page's linked session. The page sends requests only to a session recorded in its own data, and never acts on a request itself.

This matters because posting turns the page's comments and edits into review comments and commits under the owner's GitHub account. If other people could write comments, they could post in the owner's name.

## Posting never trusts stored paths

- The posting script acts only on markdown files the pull request adds or changes, as GitHub reports them when the plan is made, and again just before committing. A comment or edit naming any other path (for example a CI workflow) is skipped with a warning.
- An item's scope must name the same pull request and file as the item itself.
- Before posting, Claude shows every item with its file, line and text, and asks before committing anything.
- Commits are made against the exact version that was planned; if a file changed in between, GitHub refuses the commit.
- The scripts call `gh` with argument lists and send data on standard input, never through a shell. File paths are percent-encoded in API URLs.

## Untrusted markdown on the page

Markdown and comments from a pull request are rendered as HTML and sanitized with DOMPurify. On top of its defaults (no scripts, event handlers, `javascript:` links, frames):

- no `style`, `id`, `class`, `name`, `tabindex`, `accesskey` or `autofocus` attributes, so content cannot draw overlays, restyle the page, or take over the page's own elements;
- no form controls, buttons, dialogs, SVG or MathML, so content cannot imitate the page's controls;
- links on comment cards and the pull request title must start with `https://github.com/`.

The two libraries are loaded from cdnjs with integrity hashes, so a modified copy is refused.

## Requests from the page to Claude

- The page sends fixed sentences. A pull request reference is reduced to `OWNER/REPO#N`, with names limited to letters, digits, `.`, `-` and `_`.
- Claude treats text from pull requests, review comments, the reviewer's comments and page messages as data, not instructions.
- Anything that commits asks the reviewer in the chat first, whatever started it.

## Privacy

- Sharing the page shares the documents loaded into it, including content from private repositories.
- Edits proposed by voice ("edit make this shorter") send that section's text to Claude, on the reviewer's own account.
- Operating-system dictation (Win+H on Windows, phone keyboards) is the operating system's feature; Windows voice typing sends audio to Microsoft's speech service.
