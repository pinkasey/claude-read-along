// Records the README screenshots and the animated demo from the real page, using the test harness's
// stand-ins (speech advances on a timer instead of a voice). Regenerate after visible UI changes:
//   node tools/demo/record.js        (needs Playwright and ffmpeg)
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");
const { open, closeBrowser, prFixture } = require("../../tests/page/harness");

const OUT = path.resolve(__dirname, "..", "..", "docs", "images");
fs.mkdirSync(OUT, { recursive: true });

function fixture() {
  const fx = prFixture();
  fx["docs/current"].title = "Design: per-tenant rate limiting";
  fx["docs/current"].pr = { repo: "example/platform", number: 42, url: "https://github.com/example/platform/pull/42", headRef: "rate-limit-design" };
  fx["docs/current"].files[0].path = fx["files/f0"].path = "docs/rate-limiting.md";
  fx["files/f0"].comments.splice(1, 2); // keep the one human comment
  fx["files/f0"].comments[0].url = "https://github.com/example/platform/pull/42#discussion_r1";
  return fx;
}

async function screenshots() {
  const desk = await open({ db: fixture(), viewport: { width: 1280, height: 800 } });
  await desk.page.click('.unit[data-i="3"]'); await desk.page.waitForTimeout(150);
  await desk.end(1); await desk.page.waitForTimeout(100); // into the first sentence
  await desk.page.click("#playBtn"); // pause, keeping the highlight
  await desk.page.screenshot({ path: path.join(OUT, "screenshot-desktop.png") });
  await desk.close();

  const phone = await open({ db: fixture(), viewport: { width: 390, height: 844 } });
  await phone.page.click('.unit[data-i="3"]'); await phone.page.waitForTimeout(150);
  await phone.end(1); await phone.page.click("#playBtn");
  await phone.page.screenshot({ path: path.join(OUT, "screenshot-phone.png") });
  await phone.close();
}

async function demo() {
  const t = await open({ db: fixture(), viewport: { width: 1180, height: 760 } });
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "readalong-demo-"));
  let n = 0;
  const shot = async (times = 1) => { for (let i = 0; i < times; i++) await t.page.screenshot({ path: path.join(dir, `f${String(n++).padStart(4, "0")}.png`) }); };
  await shot(4);
  // Click a changed section: it is announced, read sentence by sentence, then its review comment.
  await t.page.click('.unit[data-i="3"]'); await t.page.waitForTimeout(100); await shot(5);
  for (let i = 0; i < 5; i++) { await t.end(1); await t.page.waitForTimeout(80); await shot(6); }
  // Dictate a comment into the command box (what Win+H or a phone keyboard would type).
  await t.page.click("#cmdIn");
  for (const ch of "add comment cite the source of 2,000") { await t.page.keyboard.type(ch); await shot(); }
  await t.page.keyboard.press("Enter"); await t.page.waitForTimeout(200); await shot(10);
  // Down arrow: the next section.
  await t.page.keyboard.press("ArrowDown"); await t.page.waitForTimeout(150); await shot(6);
  await t.end(1); await t.page.waitForTimeout(80); await shot(5);
  // Post review: the plan, and the settings.
  await t.page.click("#postBtn"); await t.page.waitForTimeout(200); await shot(14);
  await t.close();

  const gif = path.join(OUT, "demo.gif");
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", "6", "-i", path.join(dir, "f%04d.png"),
    "-vf", "scale=880:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=4",
    "-loop", "0", gif]);
  fs.rmSync(dir, { recursive: true, force: true });
  return { frames: n, gif };
}

(async () => {
  await screenshots();
  const { frames, gif } = await demo();
  await closeBrowser();
  for (const f of fs.readdirSync(OUT)) console.log(f, Math.round(fs.statSync(path.join(OUT, f)).size / 1024) + " KB");
  console.log(frames + " frames in " + path.relative(process.cwd(), gif));
})();
