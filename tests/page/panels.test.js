// The Open pull request and Post review panels: requests to Claude, the plan, settings, permissions.
const { test, after } = require("node:test");
const assert = require("node:assert/strict");
const { open, closeBrowser, prFixture } = require("./harness");

after(closeBrowser);

const withItems = () => prFixture({
  "notes/n1": { scope: "o/r#7:docs/design.md", file: "docs/design.md", key: "L7", line: 7, endLine: 7, text: "in diff" },
  "notes/n2": { scope: "o/r#7:docs/design.md", file: "docs/design.md", key: "L39", line: 39, endLine: 39, text: "outside" },
  "edits/e1": { scope: "o/r#7:docs/design.md", file: "docs/design.md", key: "L14", line: 14, endLine: 14, original: "a", text: "b" },
});

test("Open pull request accepts links and owner/repo#N, and sends the request", async () => {
  const t = await open({ db: prFixture() });
  await t.page.click("#openPrBtn");
  for (const [input, want] of [["https://github.com/a/b/pull/12", "a/b#12"], ["a/b#12", "a/b#12"], ["a/b 12", "a/b#12"], ["nonsense", null]]) {
    await t.page.fill("#prRef", input);
    const said = await t.page.textContent("#prSay");
    if (want) assert.equal(said, `Load pull request ${want} into the Read-Along page.`); else assert.match(said, /^Enter a pull request/);
  }
  await t.page.fill("#prRef", "a/b#12"); await t.page.click("#prGo"); await t.page.waitForTimeout(150);
  assert.equal(await t.page.textContent("#prStatus"), "Sent. Claude is working on it in the chat.");
  assert.deepEqual(await t.q(() => window.__sent), [{ server: "Claude Code Remote", tool: "send_message", input: { session_id: "session_test", message: "[Read-Along page] Load pull request a/b#12 into the Read-Along page." } }]);
  await t.close();
});

test("panels are modal: focus stays inside, Esc closes, focus returns to the opener", async () => {
  const t = await open({ db: withItems() });
  await t.page.click("#postBtn");
  for (let i = 0; i < 12; i++) await t.page.keyboard.press("Tab");
  assert.equal(await t.q(() => !!document.activeElement.closest("dialog")), true);
  await t.page.keyboard.press("Escape"); await t.page.waitForTimeout(100);
  assert.equal(await t.q(() => document.getElementById("panel").open), false);
  assert.equal(await t.q(() => document.activeElement.id), "postBtn");
  await t.close();
});

test("the post plan follows the settings, which are saved per person", async () => {
  const t = await open({ db: withItems() });
  await t.page.click("#postBtn");
  const plan = () => t.q(() => [...document.querySelectorAll(".pl")].map((x) => x.textContent));
  assert.deepEqual(await plan(), [
    "1comment on changed lines → review comments on those lines",
    "1edit on changed lines → suggested changes the author can apply",
    "1comment on unchanged lines → listed in the review summary",
  ]);
  assert.equal(await t.q(() => !!document.querySelector(".warnbox")), false);
  await t.page.check("input[name=em][value=commit]"); await t.page.check("input[name=out][value=anchor]"); await t.page.waitForTimeout(100);
  const p2 = await plan();
  assert.match(p2[1], /committed to feature\/x, each with a one-click revert comment/);
  assert.match(p2[2], /<!-- review comment --> marker committed/);
  assert.match(await t.page.textContent(".warnbox"), /commits to feature\/x/);
  await t.page.uncheck("#revertChk"); await t.page.waitForTimeout(150);
  assert.doesNotMatch((await plan())[1], /revert/);
  const saved = await t.store("data/users/u_me/review-settings");
  assert.deepEqual([saved.editMode, saved.outside, saved.revert], ["commit", "anchor", false]);
  await t.page.click("#postGo"); await t.page.waitForTimeout(150);
  assert.equal((await t.q(() => window.__sent))[0].input.message,
    "[Read-Along page] Post my review for o/r#7. Settings: edits on changed lines = commit inline; comments and edits on unchanged lines = commit and comment; revert comments on committed edits = off.");
  await t.close();
});

const connectorCases = [
  ["works", {}, null, /^Sent\./, 1],
  ["send tool not offered", { connector: { authStatus: "connected", tools: ["list_triggers"] } }, /doesn't let pages send messages/, null, 0],
  ["connector missing", { connector: { missing: true } }, /isn't available to this page/, null, 0],
  ["retryable failure", { connector: { authStatus: "connected", tools: ["send_message"], fail: { code: "upstream_error", retryable: true, message: "connector access isn't confirmed" } } }, null, /Try again.*connector access isn't confirmed/s, 0],
  ["permission asked and allowed", { permission: { state: "prompt", answer: "granted" } }, /asks you to allow/, /^Sent\./, 1],
  ["permission declined", { permission: { state: "prompt", answer: "denied" } }, null, /isn't allowed to message Claude/, 0],
];
for (const [name, opts, onOpen, afterPress, sends] of connectorCases) {
  test(`sending to Claude: ${name}`, async () => {
    const t = await open(Object.assign({ db: prFixture() }, opts));
    await t.page.click("#openPrBtn"); await t.page.fill("#prRef", "o/r#1"); await t.page.waitForTimeout(150);
    const opened = await t.page.textContent("#prStatus");
    if (onOpen) assert.match(opened, onOpen);
    if (!(await t.page.isDisabled("#prGo"))) { await t.page.click("#prGo"); await t.page.waitForTimeout(150); }
    if (afterPress) assert.match(await t.page.textContent("#prStatus"), afterPress);
    assert.equal((await t.q(() => window.__sent)).length, sends);
    await t.close();
  });
}

test("requests go to Claude as a comment sent to the watching session, named in the message", async () => {
  const t = await open({ db: withItems(), comments: { state: "available" } });
  await t.page.click("#openPrBtn"); await t.page.waitForTimeout(100);
  assert.match(await t.page.textContent("#prStatus"), /posts this as a comment on the page and sends it to Claude/);
  await t.page.fill("#prRef", "o/r#8");
  await t.page.click("#prGo"); await t.page.waitForTimeout(150);
  assert.deepEqual(await t.q(() => window.__commentSends), [{ anchor: { el: "docTitle" },
    text: "[Read-Along page] Load pull request o/r#8 into the Read-Along page. (For Claude session session_test.)" }]);
  assert.deepEqual(await t.q(() => window.__sent), [], "the connector is not used");
  assert.match(await t.page.textContent("#prStatus"), /^Sent\./);
  await t.page.click("#prClose");
  await t.page.click("#postBtn"); await t.page.waitForTimeout(100);
  await t.page.click("#postGo"); await t.page.waitForTimeout(150);
  assert.match((await t.q(() => window.__commentSends))[1].text, /^\[Read-Along page\] Post my review for o\/r#7\. Settings: .*\(For Claude session session_test\.\)$/);
  await t.close();
});

test("with no Claude session watching the page, the button is off and the sentence is offered", async () => {
  const t = await open({ db: withItems(), comments: { state: "no_session" } });
  await t.page.click("#openPrBtn"); await t.page.waitForTimeout(100);
  assert.match(await t.page.textContent("#prStatus"), /No Claude session is watching this page/);
  assert.equal(await t.page.isDisabled("#prGo"), true);
  await t.close();
});

test("a refused send says why and posts nothing", async () => {
  const t = await open({ db: withItems(), comments: { state: "available", fail: { code: "claude_unavailable" } } });
  await t.page.click("#openPrBtn"); await t.page.waitForTimeout(100);
  await t.page.click("#prGo"); await t.page.waitForTimeout(150);
  assert.match(await t.page.textContent("#prStatus"), /No Claude session is watching this page right now/);
  await t.close();
});
