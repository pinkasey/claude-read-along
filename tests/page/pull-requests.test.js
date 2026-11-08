// Pull requests: changed sections, review comments, outline, Changed only, files, scoping, position.
const { test, after } = require("node:test");
const assert = require("node:assert/strict");
const { open, closeBrowser, prFixture } = require("./harness");

after(closeBrowser);

test("header, changed sections, comments and outline", async () => {
  const t = await open({ db: prFixture() });
  assert.match(await t.page.textContent("#docMeta"), /o\/r #7 · docs\/design\.md · 42 sections · 4 changed · 2 comments/);
  assert.deepEqual(await t.q(() => [...document.querySelectorAll(".unit.changed .gutter")].map((g) => g.textContent)), ["7", "14", "56", "57"]);
  const cards = await t.q(() => [...document.querySelectorAll(".gh-comment")].map((c) => ({ who: c.querySelector("b").textContent, bot: c.classList.contains("bot"), outdated: c.classList.contains("outdated"), text: c.querySelector(".gh-body").textContent.trim() })));
  assert.deepEqual(cards.map((c) => [c.who, c.bot, c.outdated]), [["dana", false, false], ["ci-bot[bot]", true, false], ["sam", false, true]]);
  assert.equal(cards[0].text, "Is 2,000 still right?", "the Claude Code footer is not shown");
  const outline = await t.q(() => [...document.querySelectorAll(".ol-item")].map((o) => (o.querySelector(".dot.none") ? "" : "*") + o.querySelector(".ol-text").textContent));
  assert.ok(outline.includes("*Background") && outline.includes("Non-goals"));
  assert.deepEqual(t.errors, []);
  await t.close();
});

test("reads 'Changed.', the section, then human comments (never bots)", async () => {
  const t = await open({ db: prFixture() });
  await t.page.click('.unit[data-i="3"]'); await t.page.waitForTimeout(120);
  await t.end(6);
  assert.deepEqual(await t.spoken(), [
    "Changed.",
    "Today the public API applies one global rate limit of 2,000 requests per second, shared by every tenant.",
    "When a single large tenant runs a bulk import, smaller tenants see 429 errors even though they are well under any reasonable quota.",
    "Support logged 41 tickets about this in the last quarter.",
    "Comment from dana.",
    "Is 2,000 still right?",
  ]);
  await t.close();
});

test("the comment being read is lit up", async () => {
  const t = await open({ db: prFixture() });
  await t.page.click('.unit[data-i="3"]'); await t.page.waitForTimeout(120);
  await t.end(4);
  assert.equal(await t.q(() => document.querySelector(".gh-comment.speaking b").textContent), "dana");
  await t.close();
});

test("Changed only skips unchanged sections but keeps chapter headings", async () => {
  const t = await open({ db: prFixture() });
  await t.page.click('.unit[data-i="3"]'); await t.page.click("#playBtn");
  await t.page.check("#changedChk");
  assert.ok(await t.q(() => document.querySelectorAll(".unit.dim").length) > 20);
  await t.page.keyboard.press("ArrowDown"); await t.page.waitForTimeout(100);
  assert.equal(await t.activeLine(), "11", "the Goals heading, whose chapter has a change");
  await t.page.keyboard.press("ArrowDown"); await t.page.waitForTimeout(100);
  assert.equal(await t.activeLine(), "14");
  await t.close();
});

test("next change, next comment, next file", async () => {
  const t = await open({ db: prFixture() });
  await t.page.click("#cmdIn");
  await t.say("next change"); assert.equal(await t.activeLine(), "7");
  await t.say("next change"); assert.equal(await t.activeLine(), "14");
  await t.say("previous change"); assert.equal(await t.activeLine(), "7");
  await t.say("next comment"); assert.equal(await t.activeLine(), "25");
  await t.say("next file");
  assert.match(await t.page.textContent("#docMeta"), /docs\/other\.md/);
  assert.equal(await t.q(() => !!document.querySelector(".file-banner")), true, "a new file says so");
  await t.close();
});

test("comments are kept per file, and the reading position is recorded with its end line", async () => {
  const t = await open({ db: prFixture() });
  await t.page.click('.unit[data-i="5"]'); await t.page.waitForTimeout(1500);
  const pos = await t.store("state/position");
  assert.deepEqual([pos.line, pos.endLine, pos.file, pos.scope], [11, 11, "docs/design.md", "o/r#7:docs/design.md"]);
  await t.page.click("#cmdIn");
  await t.say("add comment check this");
  const keys = await t.storeKeys("notes/");
  const saved = await t.store(keys[0]);
  assert.deepEqual([saved.scope, saved.file, saved.line], ["o/r#7:docs/design.md", "docs/design.md", 11]);
  await t.page.selectOption("#filePick", "f1"); await t.page.waitForTimeout(150);
  assert.equal(await t.page.textContent("#chipNotes"), "0 comments");
  await t.close();
});
