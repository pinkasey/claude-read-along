// Security and data hygiene: untrusted markdown, links, view-only visitors, leftover items, old documents.
const { test, after } = require("node:test");
const assert = require("node:assert/strict");
const { open, closeBrowser, prFixture, SAMPLE } = require("./harness");

after(closeBrowser);

const HOSTILE = [
  "# Other",
  '<div id="cmdIn" class="panel" style="position:fixed;inset:0;z-index:99">Fake panel</div>',
  "<form><button>Post review</button></form>",
  '<img src=x onerror="window.__pwned=1">',
  "[x](javascript:window.__pwned=2)",
  "<svg><script>window.__pwned=3</script></svg>",
].join("\n\n");

test("pull request markdown cannot run code, draw controls, restyle or take over the page", async () => {
  const fx = prFixture();
  fx["files/f1"].markdown = HOSTILE;
  fx["files/f0"].comments[2].url = "javascript:window.__pwned=4";
  const t = await open({ db: fx });
  assert.deepEqual(await t.q(() => [...document.querySelectorAll(".gh-head a")].map((a) => a.getAttribute("href"))), ["https://github.com/o/r/pull/7#discussion_r1"], "only real GitHub links");
  await t.page.selectOption("#filePick", "f1"); await t.page.waitForTimeout(150);
  const doc = await t.q(() => document.getElementById("doc").innerHTML);
  assert.doesNotMatch(doc, /style=|<form|<button|<svg|javascript:|onerror/);
  assert.equal(await t.q(() => document.querySelectorAll("#cmdIn").length), 1);
  assert.equal(await t.q(() => document.getElementById("cmdIn").tagName), "INPUT");
  await t.page.waitForTimeout(200);
  assert.equal(await t.q(() => window.__pwned || 0), 0);
  await t.close();
});

test("libraries load only with their integrity hashes", async () => {
  const t = await open({ db: prFixture() });
  const scripts = await t.q(() => [...document.querySelectorAll("script[src]")].map((s) => ({ src: s.src, integrity: s.integrity, cors: s.crossOrigin })));
  assert.equal(scripts.length, 2);
  for (const s of scripts) { assert.match(s.src, /^https:\/\/cdnjs\.cloudflare\.com\//); assert.match(s.integrity, /^sha512-/); assert.equal(s.cors, "anonymous"); }
  assert.equal(await t.q(() => !!(window.marked && window.DOMPurify)), true, "the hashes match the files");
  await t.close();
});

test("someone else's page is view only, voice included", async () => {
  const t = await open({ db: prFixture(), owner: false });
  assert.equal(await t.page.textContent("#chipMode"), "View only");
  assert.equal(await t.page.isDisabled("#noteBtn"), true);
  assert.equal(await t.page.isDisabled("#editBtn"), true);
  assert.equal(await t.page.isHidden("#postBtn"), true);
  await t.page.click('.unit[data-i="3"]');
  await t.page.click("#cmdIn");
  await t.say("add comment sneaky");
  assert.deepEqual(await t.storeKeys("notes/"), []);
  await t.close();
});

test("comments and edits from documents that aren't loaded are listed and can be deleted", async () => {
  const t = await open({ db: prFixture({
    "notes/n1": { scope: "o/r#7:docs/design.md", file: "docs/design.md", key: "L7", line: 7, text: "current" },
    "notes/old": { key: "L7", line: 7, text: "it's actually 3000 requests per second" },
    "edits/L9": { key: "L9", line: 9, original: "This document proposes", text: "This document replaces" },
    "notes/otherpr": { scope: "x/y#5:a.md", file: "a.md", key: "L3", line: 3, text: "from another PR" },
  }) });
  const orphans = () => t.q(() => [...document.querySelectorAll(".item.orphan")].map((x) => x.querySelector(".line").textContent));
  assert.deepEqual(await orphans(), ["an earlier document · line 7", "x/y #5 · a.md · line 3", "an earlier document · line 9"]);
  assert.equal(await t.page.textContent("#chipNotes"), "1 comment", "the current file shows only its own");
  await t.page.click(".item.orphan [data-del-edit-id]"); await t.page.waitForTimeout(150);
  assert.equal((await orphans()).length, 2);
  await t.page.click("#delOrphans");
  assert.match(await t.page.textContent("#delOrphans"), /Press again/);
  await t.page.click("#delOrphans"); await t.page.waitForTimeout(300);
  assert.deepEqual(await orphans(), []);
  assert.deepEqual(await t.storeKeys("notes/"), ["notes/n1"]);
  await t.close();
});

test("an old single document gets an identity, and its scope-less items move to it", async () => {
  const t = await open({ db: {
    "docs/current": { title: "Old sample", path: "sample.md", markdown: SAMPLE },
    "notes/old": { key: "L7", line: 7, text: "old comment" },
    "edits/L9": { key: "L9", line: 9, original: "This document proposes replacing the global limit with per-tenant limits, enforced at the gateway, with a small shared burst pool.", text: "Replaced." },
  } });
  // It also moves into the kept reviews, and docs/current points to it.
  const cur = await t.store("docs/current");
  assert.match(cur.reviewId, /^r[0-9a-f]{12}$/);
  const docId = (await t.store("reviews/" + cur.reviewId)).docId;
  assert.match(docId, /^[0-9a-f]{16}$/);
  assert.equal((await t.store("notes/old")).scope, "doc:" + docId);
  assert.equal((await t.store("edits/L9")).scope, "doc:" + docId);
  assert.equal(await t.page.textContent("#chipNotes"), "1 comment");
  assert.equal(await t.q(() => document.querySelectorAll(".item.orphan").length), 0);
  await t.close();
});
