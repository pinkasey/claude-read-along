// Several reviews kept on the page: switching between them without Claude, the Open panel's list,
// removing one, and requests going to the Claude session that loaded each review.
const { test, after } = require("node:test");
const assert = require("node:assert/strict");
const { open, closeBrowser, prFixture } = require("./harness");

after(closeBrowser);

const HOUR = 3600e3;
function fixture() {
  const pr = prFixture();
  const A = Object.assign({}, pr["docs/current"], { id: "rA", sessionId: "session_A", loadedAt: new Date(Date.now() - 2 * HOUR).toISOString() });
  const B = {
    id: "rB", title: "Second PR", loadId: "x/y#3@def", defaultFile: "g0", sessionId: "session_B", loadedAt: new Date(Date.now() - 5 * 60e3).toISOString(),
    pr: { repo: "x/y", number: 3, url: "https://github.com/x/y/pull/3", headRef: "b" },
    files: [{ id: "g0", path: "README.md", status: "modified", changed: 1, comments: 0 }],
  };
  return {
    "reviews/rA": A, "reviews/rB": B,
    "files/f0": pr["files/f0"], "files/f1": pr["files/f1"],
    "files/g0": { path: "README.md", status: "modified", markdown: "# Second\n\nSecond review text.\n", added: [[3, 3]], hunks: [[1, 3]], comments: [] },
    "docs/current": { reviewId: "rB" },
    "notes/n1": { key: "L7", line: 7, endLine: 7, text: "on A", scope: "o/r#7:docs/design.md", file: "docs/design.md" },
    "config/session": { sessionId: "session_page" },
  };
}
const options = (t) => t.q(() => [...document.querySelectorAll("#reviewPick option")].map((o) => o.textContent));

test("the header lists every loaded review, most recent first, and switches between them", async () => {
  const t = await open({ db: fixture() });
  assert.equal(await t.page.textContent("#docTitle"), "Second PR");
  const opts = await options(t);
  assert.match(opts[0], /^x\/y #3 · Second PR · loaded 5 min ago$/);
  assert.match(opts[1], /^o\/r #7 · Test PR · loaded 2 h ago · 1 unposted$/);
  assert.equal(opts[2], "Open another, reload or remove…");
  await t.page.selectOption("#reviewPick", "rA"); await t.page.waitForTimeout(150);
  assert.deepEqual(await t.store("docs/current"), Object.assign({ reviewId: "rA" }, { updatedAt: (await t.store("docs/current")).updatedAt }));
  assert.equal(await t.page.textContent("#docTitle"), "Test PR");
  assert.equal(await t.page.textContent("#chipNotes"), "1 comment", "A's comment is back");
  assert.match((await options(t))[0], /^o\/r #7/, "now the most recently opened");
  assert.deepEqual(t.errors, []);
  await t.close();
});

test("each review keeps its place", async () => {
  const t = await open({ db: fixture() });
  await t.page.selectOption("#reviewPick", "rA"); await t.page.waitForTimeout(150);
  await t.page.click('.unit[data-i="5"]'); await t.page.waitForTimeout(1400); // the place is saved with the position
  await t.page.selectOption("#reviewPick", "rB"); await t.page.waitForTimeout(150);
  assert.equal(await t.activeLine(), "1");
  await t.page.selectOption("#reviewPick", "rA"); await t.page.waitForTimeout(150);
  assert.equal(await t.q(() => document.querySelector(".unit.active").dataset.i), "5");
  await t.close();
});

test("the Open panel switches to a loaded review, and asks Claude only for others", async () => {
  const t = await open({ db: fixture() });
  await t.page.selectOption("#reviewPick", "__open"); await t.page.waitForTimeout(100);
  assert.equal(await t.page.isVisible("#panel"), true);
  assert.equal(await t.page.textContent("#prGo"), "Ask Claude to reload it", "starts from the open review");
  await t.page.fill("#prRef", "o/r#7");
  assert.equal(await t.page.textContent("#prGo"), "Switch to it");
  await t.page.fill("#prRef", "o/r#8");
  assert.equal(await t.page.textContent("#prGo"), "Ask Claude to load it");
  await t.page.fill("#prRef", "https://github.com/o/r/pull/7");
  await t.page.click("#prGo"); await t.page.waitForTimeout(150);
  assert.equal(await t.page.isVisible("#panel"), false);
  assert.equal(await t.page.textContent("#docTitle"), "Test PR");
  assert.deepEqual(await t.q(() => window.__sent), [], "no message to Claude");
  await t.close();
});

test("the Open panel lists the reviews; one can be opened or removed, keeping its unposted items", async () => {
  const t = await open({ db: fixture() });
  await t.page.click("#openPrBtn");
  assert.deepEqual(await t.q(() => [...document.querySelectorAll(".reviews-list .rv-sub")].map((e) => e.textContent)),
    ["loaded 5 min ago · open now", "loaded 2 h ago · 1 unposted"]);
  t.page.once("dialog", (d) => { assert.match(d.message(), /Its 1 unposted comments and edits are kept/); d.accept(); });
  await t.page.click('[data-rv-remove="rA"]'); await t.page.waitForTimeout(200);
  assert.deepEqual(await t.storeKeys("reviews/"), ["reviews/rB"]);
  assert.deepEqual(await t.storeKeys("files/"), ["files/g0"]);
  assert.ok(await t.store("notes/n1"), "the comment is kept");
  assert.equal(await t.page.isHidden("#reviewPick"), true, "one review left: no picker");
  await t.close();
});

test("removing the open review opens the next one", async () => {
  const t = await open({ db: fixture() });
  await t.page.click("#openPrBtn");
  t.page.once("dialog", (d) => d.accept());
  await t.page.click('[data-rv-remove="rB"]'); await t.page.waitForTimeout(200);
  assert.equal((await t.store("docs/current")).reviewId, "rA");
  await t.close();
});

test("requests about a review go to the session that loaded it", async () => {
  const t = await open({ db: fixture(), permission: { state: "granted" } });
  await t.page.click("#openPrBtn");
  await t.page.click("#prGo"); await t.page.waitForTimeout(150);
  await t.page.click("#prClose");
  await t.page.selectOption("#reviewPick", "rA"); await t.page.waitForTimeout(150);
  await t.page.click("#openPrBtn");
  await t.page.click("#prGo"); await t.page.waitForTimeout(150);
  assert.deepEqual(await t.q(() => window.__sent.map((x) => [x.input.session_id, x.input.message])), [
    ["session_B", "[Read-Along page] Load pull request x/y#3 into the Read-Along page."],
    ["session_A", "[Read-Along page] Load pull request o/r#7 into the Read-Along page."],
  ]);
  await t.close();
});

test("a review loaded before reviews were kept moves into them", async () => {
  const t = await open({ db: prFixture() });
  const cur = await t.store("docs/current");
  assert.match(cur.reviewId, /^r[0-9a-f]{12}$/);
  const rev = await t.store("reviews/" + cur.reviewId);
  assert.deepEqual([rev.title, rev.pr.number, rev.files.length], ["Test PR", 7, 2]);
  assert.equal(await t.page.textContent("#docTitle"), "Test PR");
  await t.close();
});

test("comments in other loaded reviews are not 'other documents'", async () => {
  const t = await open({ db: fixture() });
  assert.equal(await t.q(() => document.querySelectorAll(".item.orphan").length), 0);
  await t.close();
});
