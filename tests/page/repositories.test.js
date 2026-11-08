// Repository reviews: markdown read from a branch without a pull request, and the draft pull request
// that posting opens.
const { test, after } = require("node:test");
const assert = require("node:assert/strict");
const { open, closeBrowser, repoFixture } = require("./harness");

after(closeBrowser);

const REVIEW_PR = { repo: "o/r", number: 9, url: "https://github.com/o/r/pull/9", headRef: "read-along/review-1", draft: true };
const item = (extra) => Object.assign({ scope: "o/r@main:docs/design.md", file: "docs/design.md", key: "L7", line: 7, endLine: 7 }, extra);

test("a repository is read like a pull request, without change markers", async () => {
  const t = await open({ db: repoFixture() });
  assert.match(await t.page.textContent("#docMeta"), /^o\/r @ main · docs\/design\.md · 42 sections$/);
  assert.equal(await t.page.getAttribute("#docMeta a", "href"), "https://github.com/o/r/tree/main/docs");
  assert.equal(await t.q(() => document.querySelectorAll(".unit.changed").length), 0);
  assert.equal(await t.page.isHidden("#changedLbl"), true);
  await t.page.click('.unit[data-i="3"]'); await t.page.waitForTimeout(100);
  assert.match(await t.lastSpoken(), /^Today the public API/, "no 'Changed.' before it");
  assert.deepEqual(t.errors, []);
  await t.close();
});

test("comments are scoped to the repository review, per file", async () => {
  const t = await open({ db: repoFixture() });
  await t.page.click('.unit[data-i="3"]');
  await t.page.click("#cmdIn");
  await t.say("add comment needs a source");
  const keys = await t.storeKeys("notes/");
  const saved = await t.store(keys[0]);
  assert.deepEqual([saved.scope, saved.file, saved.line], ["o/r@main:docs/design.md", "docs/design.md", 7]);
  await t.close();
});

test("the Open panel takes repositories as well as pull requests", async () => {
  const t = await open({ db: repoFixture() });
  await t.page.click("#openPrBtn");
  assert.equal(await t.page.inputValue("#prRef"), "o/r@main:docs", "starts from what is loaded");
  const cases = [
    ["owner/repo", "Load repository owner/repo into the Read-Along page."],
    ["owner/repo@dev", "Load repository owner/repo (branch dev) into the Read-Along page."],
    ["owner/repo@dev:docs/specs", "Load repository owner/repo (branch dev, folder docs/specs) into the Read-Along page."],
    ["owner/repo:docs", "Load repository owner/repo (folder docs) into the Read-Along page."],
    ["https://github.com/owner/repo/tree/main/docs", "Load repository owner/repo (branch main, folder docs) into the Read-Along page."],
    ["https://github.com/owner/repo", "Load repository owner/repo into the Read-Along page."],
    ["owner/repo#12", "Load pull request owner/repo#12 into the Read-Along page."],
  ];
  for (const [input, want] of cases) { await t.page.fill("#prRef", input); assert.equal(await t.page.textContent("#prSay"), want, input); }
  await t.page.fill("#prRef", "owner/repo:../secrets");
  assert.match(await t.page.textContent("#prSay"), /^Enter a pull request/, "a folder cannot leave the repository");
  await t.close();
});

test("posting a repository review creates a draft pull request, and needs a commit", async () => {
  const t = await open({ db: repoFixture({ "notes/n1": item({ text: "a comment" }) }) });
  await t.page.click("#postBtn");
  assert.equal(await t.page.textContent("#panelTitle"), "Create a review pull request in o/r");
  assert.match(await t.page.textContent(".warnbox"), /needs at least one commit/);
  assert.equal(await t.page.isDisabled("#postGo"), true, "comments only, listed in the summary: nothing to commit");
  await t.page.check("input[name=out][value=anchor]"); await t.page.waitForTimeout(100);
  assert.equal(await t.page.isDisabled("#postGo"), false);
  assert.match(await t.page.textContent(".warnbox"), /opens a draft pull request/);
  assert.equal(await t.page.textContent("#postGo"), "Ask Claude to create it");
  await t.page.click("#postGo"); await t.page.waitForTimeout(150);
  assert.match((await t.q(() => window.__sent))[0].input.message, /^\[Read-Along page\] Post my review for o\/r \(branch main, folder docs\)\./);
  await t.close();
});

test("once the review pull request exists, comments stay and later posts go to it", async () => {
  const t = await open({ db: repoFixture({ "notes/n1": item({ text: "posted earlier? no, still pending" }) }, REVIEW_PR) });
  assert.match(await t.page.textContent("#docMeta"), /o\/r @ main · review PR #9 \(draft\) · docs\/design\.md/);
  assert.equal(await t.page.textContent("#chipNotes"), "1 comment", "the scope did not change when the pull request was created");
  await t.page.click("#postBtn");
  assert.equal(await t.page.textContent("#panelTitle"), "Post review to o/r#9");
  assert.equal(await t.q(() => document.querySelectorAll(".item.orphan").length), 0);
  await t.close();
});
