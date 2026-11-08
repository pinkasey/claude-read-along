# Read-Along documentation

These documents describe how Read-Along behaves: what it is for, what each part does, and the rules it follows. They are the reference for building and reviewing changes. The code should match them, and a change in behavior changes them in the same pull request.

| Document | What it covers |
| --- | --- |
| [product.md](product.md) | The problem, who it is for, goals, non-goals, principles, and the platform limits the design works within |
| [features/reading.md](features/reading.md) | Listening: sections, highlighting, navigation, speed, voices, outline, keyboard |
| [features/voice-commands.md](features/voice-commands.md) | The command box, voice mode, and every command |
| [features/comments-and-edits.md](features/comments-and-edits.md) | The reviewer's comments and edits: where they attach, how they are kept apart per document, undo |
| [features/pull-requests.md](features/pull-requests.md) | Loading a pull request: files, changed sections, existing review comments |
| [features/repositories.md](features/repositories.md) | Reading a repository or folder without a pull request, and the review pull request opened when posting |
| [features/posting-reviews.md](features/posting-reviews.md) | Posting a review: the two settings, what gets commented or committed, confirmation |
| [features/page-and-sessions.md](features/page-and-sessions.md) | Where the page lives, what needs a Claude session, how the page and Claude talk, stored data |
| [features/plugin.md](features/plugin.md) | The Claude Code plugin: installing, requirements, what the skill does, disclaimer |
| [development.md](development.md) | Tests and CI: what each job checks, how to run them, rules for changes |
| [security.md](security.md) | Who can change what, how posting guards against forged data, untrusted markdown, privacy |

## Status labels

Each feature document marks its parts:

- **Shipped**: built and on the default branch. A pull request that builds a feature marks it Shipped (with the pull request's link) in that same pull request: once merged, it is shipped.
- **Planned**: agreed, not built yet.

## Adding a feature

1. Add a section to the feature document it belongs to, or a new file under `features/` when it is a new area. Link a new file from the table above.
2. Describe behavior from the reviewer's side: what they do, what they see and hear, and the rules the feature follows. Write each rule so it can be checked.
3. Mark it **Planned** when it is agreed but not built. The pull request that builds it marks it **Shipped**, linking to itself; there is no separate status while it is open.
4. Add tests for it (see [development.md](development.md)).
5. When a feature changes a rule in another document, change that document too.
