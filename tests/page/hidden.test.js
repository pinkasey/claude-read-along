// Front matter and <!-- comments -->: GitHub hides them, the page shows them, and reads them only on request.
const { test, after } = require("node:test");
const assert = require("node:assert/strict");
const { open, closeBrowser, repoFixture } = require("./harness");

after(closeBrowser);

const MD = [
  "---",                                   // 1
  "title: Rate limits",                    // 2
  "owner: platform",                       // 3
  "---",                                   // 4
  "",                                      // 5
  "# Intro",                               // 6
  "",                                      // 7
  "<!-- TODO: check the numbers -->",      // 8
  "",                                      // 9
  "First sentence. <!-- inline note --> Second sentence.", // 10
  "",                                      // 11
  "```html",                               // 12
  "<!-- not a comment, code -->",          // 13
  "```",                                   // 14
  "",
].join("\n");

function fixture() {
  const fx = repoFixture();
  fx["files/f0"].markdown = MD;
  return fx;
}
// Ends what is being said, and waits out the pause before the next section.
const next = async (t, n = 1) => { for (let i = 0; i < n; i++) { await t.end(1); await t.page.waitForTimeout(600); } };
const units = (t) => t.q(() => [...document.querySelectorAll(".unit")].map((u) => [u.querySelector(".gutter").textContent, u.querySelector(".body").textContent.replace(/\s+/g, " ").trim()]));

test("front matter and comments are shown, with the right line numbers", async () => {
  const t = await open({ db: fixture() });
  const u = await units(t);
  assert.deepEqual(u.map((x) => x[0]), ["1", "6", "8", "10", "12"]);
  assert.match(u[0][1], /^Front matter\s*title: Rate limits owner: platform$/);
  assert.equal(u[1][1], "Intro", "front matter is not read as a heading");
  assert.match(u[2][1], /^Comment\s*TODO: check the numbers$/);
  assert.equal(await t.q(() => document.querySelector('.unit[data-i="3"] .md-hidden').textContent), "inline note");
  assert.equal(await t.q(() => document.querySelector('.unit[data-i="4"] code').textContent.trim()), "<!-- not a comment, code -->");
  assert.equal(await t.q(() => document.querySelectorAll('.unit[data-i="4"] .md-hidden').length), 0, "code is left alone");
  assert.deepEqual(t.errors, []);
  await t.close();
});

test("by default they are announced, not read", async () => {
  const t = await open({ db: fixture() });
  await t.page.click('.unit[data-i="0"]'); await t.page.waitForTimeout(100);
  assert.equal(await t.lastSpoken(), "Front matter, 2 lines.");
  await next(t); assert.equal(await t.lastSpoken(), "Intro");
  await next(t); assert.equal(await t.lastSpoken(), "Hidden comment.");
  await next(t); assert.equal(await t.lastSpoken(), "First sentence.");
  await next(t); assert.equal(await t.lastSpoken(), "Second sentence.");
  await t.close();
});

test("Read hidden reads them", async () => {
  const t = await open({ db: fixture() });
  await t.page.check("#hiddenChk");
  await t.page.click('.unit[data-i="0"]'); await t.page.waitForTimeout(100);
  await next(t); assert.equal(await t.lastSpoken(), "title: Rate limits");
  await next(t); assert.equal(await t.lastSpoken(), "owner: platform");
  await next(t, 2); assert.equal(await t.lastSpoken(), "Hidden comment.");
  await next(t); assert.equal(await t.lastSpoken(), "TODO: check the numbers");
  await next(t); assert.equal(await t.lastSpoken(), "First sentence.");
  await next(t); assert.equal(await t.lastSpoken(), "inline note Second sentence.");
  await t.close();
});

test("a comment cannot inject markup", async () => {
  const fx = fixture();
  fx["files/f0"].markdown = "Text <!-- <img src=x onerror=alert(1)> --> more\n\n<!-- <b class=\"x\">bold</b> -->\n";
  const t = await open({ db: fx });
  assert.equal(await t.q(() => document.querySelectorAll("#doc img, #doc b").length), 0);
  assert.equal(await t.q(() => document.querySelector(".md-hidden").textContent), "<img src=x onerror=alert(1)>");
  assert.deepEqual(t.errors, []);
  await t.close();
});
