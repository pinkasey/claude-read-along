# Read-Along: product overview

## Problem

Reviewing long markdown documents (design docs, specs, READMEs) in pull requests takes a long time to read on screen, and some reviewers take in text better by listening. Existing read-aloud tools read text, but none of them connect listening to reviewing: adding review comments on what was just heard, editing it, and turning that into a pull request review.

## Who it is for

A reviewer who uses Claude Code (web, desktop app or terminal) and reviews markdown in GitHub pull requests. They may be at a desk on Windows or on a phone, and they prefer to listen while following the text on screen.

## Goals

1. Listen to a markdown document section by section, while seeing exactly what is being read.
2. Move around by clicking, by keyboard, or by voice, without losing the place.
3. Capture review comments and edits at the moment of listening, without typing if the reviewer prefers.
4. Keep everything private and local to the review until the reviewer decides to post.
5. Post the review to the pull request the way the reviewer prefers, with no surprises: nothing is committed without confirmation.
6. Work for plain markdown files too, without a pull request.

## Non-goals

- Reading code diffs aloud. Read-Along is for prose in markdown.
- Listening with the screen off. Browsers stop speech when the screen locks; the page keeps the screen awake instead.
- Premium voices from paid text-to-speech services. Reading uses the voices the browser and operating system provide.
- Approving or merging pull requests.

## Principles

- **The reviewer stays in control of anything public.** Comments and edits stay on the page until the reviewer asks Claude to post. Claude shows what it will do and asks before committing.
- **What you hear is what you see.** The section and sentence being read are highlighted and kept in view.
- **Never lose the place.** Clicking, keys and voice all move the same reading position; switching files or documents starts the new one from the top.
- **Documents never mix.** Comments and edits belong to one file of one pull request (or one loaded document) and are never shown or applied elsewhere.
- **Work without Claude where possible.** Listening, comments, edits and local files work on the page alone. Only GitHub actions need a Claude session.
- **Degrade, don't break.** When a capability is missing (speech, sentence highlighting, messaging Claude), the page says so and offers the next best way.

## Platform constraints

These limits shape the design and are not expected to change soon.

| Constraint | Consequence |
| --- | --- |
| The page runs as a claude.ai Artifact in a locked-down frame that cannot reach other websites. | The page cannot call GitHub. Claude, in a Claude Code session, loads pull requests and posts reviews. |
| The frame cannot use the microphone for this user. | Voice commands use the operating system's dictation (Win+H on Windows, the keyboard microphone on phones) typing into a command box. |
| Speech plays only after the reviewer interacts with the page, and usually stops when a phone's screen locks. | Playback starts from a button or a click; the page asks to keep the screen awake. |
| GitHub accepts review comments only on lines inside the pull request's diff. | Comments and edits elsewhere are listed in the review summary, or committed so they can be commented on (the reviewer's choice). |
| A Claude Code session ends when it is idle or closed. | The page's requests to Claude go to the session that last loaded it; if that session is gone, the page shows the sentence to paste into a new one. |

## Status

| Area | Status |
| --- | --- |
| Reading, voice commands, comments and edits, pull requests, posting reviews | In review ([#2](https://github.com/pinkasey/claude-read-along/pull/2)) |
| Packaging as a Claude Code plugin, installation | Planned |
| The page starting its own Claude session when none is available | Planned (depends on the platform allowing it) |
