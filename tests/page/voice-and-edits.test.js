// Voice commands, comments and edits, undo, drafts, and keeping documents apart.
const { test, after } = require("node:test");
const assert = require("node:assert/strict");
const { open, closeBrowser, prFixture, SAMPLE_LOCAL } = require("./harness");

after(closeBrowser);

test("navigation commands, with dictation punctuation ignored", async () => {
  const t = await open({ local: SAMPLE_LOCAL });
  await t.page.click("#cmdIn");
  assert.match(await t.say("Next."), /next/); assert.equal(await t.activeLine(), "3");
  await t.say("next chapter"); assert.equal(await t.activeLine(), "5");
  await t.say("go to line 40"); assert.equal(await t.activeLine(), "39");
  await t.say("previous chapter"); assert.equal(await t.activeLine(), "25");
  await t.say("from the top"); assert.equal(await t.activeLine(), "1");
  assert.match(await t.say("blah blah"), /Didn't recognise/);
  assert.deepEqual(t.errors, []);
  await t.close();
});

test("a dictated comment lands on the section being read when dictation started", async () => {
  const t = await open({ local: SAMPLE_LOCAL });
  await t.page.click('.unit[data-i="3"]'); await t.page.waitForTimeout(100);
  await t.page.click("#cmdIn");
  await t.page.type("#cmdIn", "add comment it's actually 3000");
  await t.page.click('.unit[data-i="5"]'); // reading moves on while the reviewer is still talking
  await t.page.waitForTimeout(3300);   // a comment waits about three seconds for more words
  assert.match(await t.page.textContent("#cmdFeedback"), /Comment added on line 7: “It's actually 3000”/);
  assert.equal(await t.page.textContent("#chipNotes"), "1 comment");
  await t.close();
});

test("change X to Y keeps the number style, accept saves, undo removes", async () => {
  const t = await open({ local: SAMPLE_LOCAL });
  await t.page.click('.unit[data-i="3"]'); await t.page.waitForTimeout(100);
  await t.page.click("#cmdIn");
  await t.say("change 2000 to 3000");
  assert.match(await t.page.inputValue("#composerText"), /rate limit of 3,000 requests/);
  await t.say("accept");
  assert.equal(await t.page.textContent("#chipEdits"), "1 edit");
  assert.match(await t.page.textContent('.unit[data-i="3"] .body'), /3,000/);
  await t.say("undo");
  assert.equal(await t.page.textContent("#chipEdits"), "0 edits");
  await t.close();
});

test("the Comment button and C key open the comment box; Save comment saves", async () => {
  const t = await open({ local: SAMPLE_LOCAL });
  await t.page.click('.unit[data-i="1"]'); await t.page.keyboard.press("c");
  assert.match(await t.page.textContent(".composer label"), /Your comment on line 3/);
  await t.page.fill("#composerText", "typed comment"); await t.page.click('[data-act="save-note"]');
  assert.equal(await t.page.textContent(".inline-note b"), "Your comment");
  assert.equal(await t.page.textContent(".item.note .kind"), "Comment");
  await t.close();
});

test("asking Claude for an edit proposes it; a code section keeps its fences", async () => {
  const t = await open({ db: prFixture(), sample: "```lua\nreturn 2\n```" });
  const codeIndex = await t.q(() => [...document.querySelectorAll(".unit")].findIndex((u) => u.classList.contains("t-code")));
  await t.page.click(`.unit[data-i="${codeIndex}"]`); await t.page.waitForTimeout(100);
  await t.page.click("#cmdIn");
  await t.say("edit return two instead"); await t.page.waitForTimeout(200);
  assert.equal(await t.page.inputValue("#composerText"), "```lua\nreturn 2\n```");
  await t.close();
});

test("a voice edit is dropped when the file changes before Claude answers", async () => {
  const t = await open({ db: prFixture(), sample: "Shorter.", sampleDelay: 300 });
  await t.page.click('.unit[data-i="3"]'); await t.page.waitForTimeout(100);
  await t.page.click("#cmdIn");
  await t.page.fill("#cmdIn", "edit make it shorter"); await t.page.press("#cmdIn", "Enter");
  await t.page.selectOption("#filePick", "f1");
  await t.page.waitForTimeout(500);
  assert.match(await t.page.textContent("#cmdFeedback"), /moved to another file/);
  assert.equal(await t.q(() => !!document.getElementById("composerText")), false);
  await t.close();
});

test("unsaved comment text survives a redraw", async () => {
  const t = await open({ db: prFixture() });
  await t.page.click('.unit[data-i="1"]'); await t.page.click("#noteBtn");
  await t.page.fill("#composerText", "half-written");
  await t.q(async () => { const db = await window.claude.use("db"); await db.collection("notes").doc("zz").set({ scope: "x", key: "L1", line: 1, text: "y" }); });
  await t.page.waitForTimeout(100);
  assert.equal(await t.page.inputValue("#composerText"), "half-written");
  await t.close();
});

test("pasted documents never share comments and edits; a new one starts at the top", async () => {
  const t = await open({});
  const paste = async (md) => { await t.page.click("#loadBtn"); await t.page.fill("#pasteIn", md); await t.page.click("#pasteBtn"); await t.page.waitForTimeout(150); };
  await paste("# Doc A\n\nAlpha one. Alpha two.\n");
  await t.page.click('.unit[data-i="1"]'); await t.page.waitForTimeout(100);
  await t.end(); await t.page.click("#playBtn");
  await t.page.click("#noteBtn"); await t.page.fill("#composerText", "on A"); await t.page.click('[data-act="save-note"]');
  await paste("# Doc B\n\nBeta one.\n");
  assert.equal(await t.page.textContent("#chipNotes"), "0 comments");
  await t.q(() => { window.__spoken.length = 0; });
  await t.page.click("#playBtn"); await t.page.waitForTimeout(120);
  assert.equal(await t.lastSpoken(), "Doc B");
  await t.close();
});
