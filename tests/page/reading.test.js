// Reading: sections, speech, sentence highlighting, navigation keys, header, focus.
const { test, after } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");
const { open, closeBrowser, SAMPLE_LOCAL, wrappedPage } = require("./harness");

after(closeBrowser);

const SMALL = { title: "T", path: "x.md", markdown: "# Title\n\nAlpha one. Alpha two. Alpha three.\n\nBeta one. Beta two.\n\nGamma one.\n" };

test("splits a document into sections with their file line numbers", async () => {
  const t = await open({ local: SAMPLE_LOCAL });
  const units = await t.q(() => [...document.querySelectorAll(".unit")].map((u) => [u.querySelector(".gutter").textContent, u.className.match(/t-(\w+)/)[1]]));
  assert.equal(units.length, 42);
  assert.deepEqual(units[0], ["1", "heading"]);
  assert.ok(units.some(([line, type]) => line === "71" && type === "item"), "a nested bullet is its own section");
  const markers = await t.q(() => [...document.querySelectorAll(".li .marker")].map((m) => m.textContent));
  for (const m of ["•", "1.", "☑", "☐"]) assert.ok(markers.includes(m), "marker " + m);
  assert.deepEqual(t.errors, []);
  await t.close();
});

test("reads sentence by sentence, highlights the spoken sentence, and continues", async () => {
  const t = await open({ local: SAMPLE_LOCAL });
  await t.page.click('.unit[data-i="3"]');
  await t.page.waitForTimeout(150);
  const first = await t.lastSpoken();
  assert.match(first, /^Today the public API applies one global rate limit of 2,000/);
  assert.equal(await t.highlighted(), first);
  await t.end(3);
  await t.page.waitForTimeout(400); // the page pauses briefly between sections
  assert.equal(await t.activeLine(), "9", "Continuous moves to the next section");
  assert.match(await t.lastSpoken(), /^This document proposes/);
  await t.close();
});

test("tables, code and task items are spoken in words", async () => {
  const t = await open({ local: SAMPLE_LOCAL });
  const speak = async (line) => {
    const i = await t.q((l) => [...document.querySelectorAll(".unit")].findIndex((u) => u.querySelector(".gutter").textContent === l), line);
    await t.page.click(`.unit[data-i="${i}"]`); await t.page.waitForTimeout(120);
    return t.lastSpoken();
  };
  assert.match(await speak("31"), /^Table with 3 rows\./);
  assert.equal(await speak("41"), "Code block in lua, 6 lines.");
  assert.equal(await speak("77"), "Done: Latency benchmark on staging");
  await t.close();
});

test("left and right move by sentence, up and down by section", async () => {
  const t = await open({ local: SMALL });
  const key = async (k) => { await t.page.keyboard.press(k); await t.page.waitForTimeout(120); };
  await t.page.click('.unit[data-i="1"]'); await t.page.waitForTimeout(120);
  assert.equal(await t.lastSpoken(), "Alpha one.");
  await key("ArrowRight"); assert.equal(await t.lastSpoken(), "Alpha two.");
  await key("ArrowRight"); await key("ArrowRight"); assert.equal(await t.lastSpoken(), "Beta one.", "crosses into the next section");
  await key("ArrowLeft"); assert.equal(await t.lastSpoken(), "Alpha three.", "and back");
  await key("ArrowDown"); assert.equal(await t.lastSpoken(), "Beta one.");
  await key("ArrowUp"); assert.equal(await t.lastSpoken(), "Alpha one.");
  await key(" "); // pause
  await key("ArrowRight"); assert.equal(await t.highlighted(), "Alpha two.", "paused: highlights");
  await key(" "); assert.equal(await t.lastSpoken(), "Alpha two.", "play starts from the highlighted sentence");
  assert.equal(await t.q(() => scrollY), 0, "arrow keys do not scroll the page");
  await t.close();
});

test("the empty command box keeps the playback keys", async () => {
  const t = await open({ local: SMALL });
  await t.page.click('.unit[data-i="1"]'); await t.page.waitForTimeout(100);
  await t.page.click("#cmdIn");
  await t.page.keyboard.press("ArrowRight"); await t.page.waitForTimeout(100);
  assert.equal(await t.lastSpoken(), "Alpha two.");
  await t.page.keyboard.press(" "); await t.page.waitForTimeout(100);
  assert.equal(await t.page.inputValue("#cmdIn"), "", "Space did not type");
  await t.close();
});

test("speed goes up to 3x", async () => {
  const t = await open({ local: SMALL });
  const rates = await t.q(() => [...document.querySelectorAll("#rateSel option")].map((o) => o.value));
  assert.deepEqual(rates.slice(-3), ["2", "2.5", "3"]);
  await t.close();
});

for (const vp of [{ width: 1280, height: 800, name: "desktop" }, { width: 390, height: 844, name: "phone" }]) {
  test(`the header stays in view while scrolling (${vp.name})`, async () => {
    const t = await open({ local: SAMPLE_LOCAL, viewport: vp });
    await t.q(() => window.scrollTo(0, 2500)); await t.page.waitForTimeout(150);
    const r = await t.q(() => {
      const h = document.querySelector("header.top").getBoundingClientRect();
      return { top: Math.round(h.top), height: h.height, wide: document.documentElement.scrollWidth > innerWidth, scrolled: scrollY };
    });
    assert.ok(r.scrolled > 1000);
    assert.equal(r.top, 0);
    assert.ok(r.height < (vp.name === "phone" ? 160 : 130), "header height " + r.height);
    assert.equal(r.wide, false, "no sideways scroll");
    if (vp.name === "phone") {
      const title = await t.q(() => { const h = document.getElementById("docTitle"); return { lines: Math.round(h.getBoundingClientRect().height / parseFloat(getComputedStyle(h).lineHeight)), text: h.textContent }; });
      assert.equal(title.lines, 1, "a long title stays on one line: " + title.text);
    }
    await t.close();
  });
}

test("in voice mode the page never takes focus from outside it", async () => {
  // The page sits in a side pane (a frame) next to Claude's chat box.
  const dir = path.dirname(wrappedPage());
  fs.writeFileSync(path.join(dir, "outer.html"), '<!doctype html><html><body style="display:flex;margin:0"><textarea id="chat"></textarea><iframe src="page.html" style="flex:1;height:900px;border:0"></iframe></body></html>');
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1500, height: 900 } });
  await context.addInitScript((doc) => { if (window.top !== window) localStorage.setItem("mdr:doc", JSON.stringify(doc)); }, SMALL);
  const page = await context.newPage();
  await page.goto("file://" + path.join(dir, "outer.html")); await page.waitForTimeout(800);
  const frame = page.frame({ url: /page\.html/ });
  await frame.click("#cmdIn");
  await frame.click('.unit[data-i="1"]'); await page.waitForTimeout(200);
  assert.equal(await frame.evaluate(() => document.activeElement.id), "cmdIn", "clicking a section keeps the command box");
  await page.click("#chat"); await page.keyboard.type("hello"); await page.waitForTimeout(400);
  assert.equal(await page.evaluate(() => document.activeElement.id), "chat");
  assert.equal(await page.inputValue("#chat"), "hello");
  await browser.close();
});

test("on a phone the settings fold behind a Settings button; on a desktop they are always shown", async () => {
  const phone = await open({ local: SMALL, viewport: { width: 390, height: 844 } });
  const state = (t) => t.q(() => ({ shown: getComputedStyle(document.querySelector(".player .settings")).display !== "none", button: getComputedStyle(document.getElementById("settingsBtn")).display !== "none", player: document.querySelector(".player").offsetHeight }));
  const folded = await state(phone);
  assert.deepEqual([folded.shown, folded.button], [false, true]);
  await phone.page.click("#settingsBtn");
  const open1 = await state(phone);
  assert.equal(open1.shown, true);
  assert.ok(open1.player > folded.player + 40, `the player grows when opened (${folded.player} -> ${open1.player})`);
  assert.equal(await phone.page.getAttribute("#settingsBtn", "aria-expanded"), "true");
  await phone.page.click("#settingsBtn");
  assert.equal((await state(phone)).shown, false);
  await phone.close();
  const desk = await open({ local: SMALL });
  const d = await state(desk);
  assert.deepEqual([d.shown, d.button], [true, false]);
  await desk.close();
});

for (const vp of [{ width: 1280, height: 800, name: "desktop" }, { width: 390, height: 844, name: "phone" }]) {
  test(`the top and bottom panels fold to one line and unfold (${vp.name})`, async () => {
    const t = await open({ local: SAMPLE_LOCAL, viewport: vp });
    const h = () => t.q(() => ({ header: document.querySelector("header.top").offsetHeight, player: document.querySelector(".player").offsetHeight }));
    const before = await h();
    await t.page.click("#foldHeader"); await t.page.click("#foldPlayer"); await t.page.waitForTimeout(100);
    const folded = await h();
    assert.ok(folded.header <= 48, "folded top panel " + folded.header);
    assert.ok(folded.player <= 120, "folded bottom panel " + folded.player);
    assert.equal(await t.page.isVisible("#docTitle"), true);
    assert.equal(await t.page.isVisible("#playBtn"), true, "play stays in reach");
    assert.equal(await t.page.isVisible("#cmdIn"), false);
    assert.equal(await t.page.getAttribute("#foldHeader", "aria-expanded"), "false");
    await t.page.click("#playBtn"); await t.page.waitForTimeout(100);
    assert.ok(await t.lastSpoken(), "playing works while folded");
    await t.page.reload(); await t.page.waitForTimeout(400);
    assert.deepEqual(await h(), folded, "remembered after reload");
    await t.page.click("#foldHeader"); await t.page.click("#foldPlayer"); await t.page.waitForTimeout(100);
    assert.deepEqual(await h(), before, "unfolds to the same size");
    await t.close();
  });
}

