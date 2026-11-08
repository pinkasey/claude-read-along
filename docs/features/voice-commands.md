# Voice commands

Status: **In review**

The page cannot use the microphone itself (see [product.md](../product.md#platform-constraints)). Voice commands are dictated into the **command box** above the player with the operating system's dictation: Win+H on Windows, the keyboard's microphone on phones. Typing into the box works the same way.

## Voice mode

- Voice mode is on while the microphone button next to the box is highlighted. Clicking the box or the button turns it on; the button or Esc turns it off.
- In voice mode, clicking a section or a player button keeps the cursor in the command box, so dictation can continue.
- The page takes the cursor back only while the reviewer is working inside the page. Clicking outside it (Claude's chat box, a claude.ai permission prompt) leaves the cursor there.
- Selecting text outside sections works in voice mode.
- While the box is empty, Space plays or pauses and ← → move between sections.

## Running a command

- A short command runs after about one second without new text. A note or an edit waits about three seconds, so a pause in mid-sentence does not cut it off; the line under the box shows what will be saved.
- Enter runs the command at once.
- Dictation's punctuation and capitals are ignored ("Next." works), as are leading fillers such as "please", "OK", "um".
- An unknown command is shown back ("Didn't recognise …") and nothing happens.

## Commands

| Group | Say | Does |
| --- | --- | --- |
| Reading | play, continue, resume | Read from the current position |
| | pause, stop, wait | Pause |
| | next, skip | Next section |
| | back, previous | Previous section |
| | repeat, again | Read the section again |
| | faster, slower | One speed step up or down |
| Moving | next chapter, previous chapter, start of chapter | Move by headings |
| | go to line N | Read from the section at line N |
| | from the top | Read from the start |
| Pull request | next change, previous change | The start of the next or previous run of changed sections |
| | next comment | The next section with a review comment (bots excluded) |
| | next file, previous file | Switch file |
| Notes | add note TEXT (also: note, comment, make a note) | Save TEXT as a note |
| | note (alone) | Open the note box to type |
| Edits | change X to Y (also: replace X with Y) | Propose replacing X with Y in the section |
| | edit INSTRUCTION (also: rewrite, fix) | Ask Claude to apply INSTRUCTION to the section, and propose the result |
| | edit (alone) | Open the edit box to type |
| | accept, yes, save / cancel, no, discard | Accept or drop the proposed edit |
| | undo | Remove the last note or edit made by voice |
| Help | commands, help | Show the command list |

## Which section a command applies to

Notes and edits apply to the section that was being read when the reviewer **started** dictating, even if reading has moved on since.

## Proposed edits

- "change X to Y" is applied in the page when X appears exactly once in the section. Numbers match with or without thousands separators, and the replacement keeps the document's style: replacing "2,000" with a dictated "3000" writes "3,000".
- Otherwise, and for "edit …", the page asks Claude (using the reviewer's own Claude usage; the first time, claude.ai asks for permission). A code section keeps its code fences.
- A proposal pauses reading, opens the section's edit box with the proposed text, and reads it aloud, followed by "Say accept, or cancel." The reviewer can also change the text by hand.
- Accepting saves the edit and continues reading from the next section if reading was on. Cancelling continues from the same section.
- A proposal belongs to its file. If the file changes before Claude answers, or while the proposal is open, it is dropped.
