// Opens page/read-along-review.html in headless Chromium with stand-ins for what claude.ai gives it:
// speech synthesis, the page database, the viewer, the Claude Code connector, permissions and
// "ask Claude". Each test describes the situation; the page runs unmodified.
const { chromium } = require("playwright");
const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");
const SAMPLE = fs.readFileSync(path.join(ROOT, "examples", "sample-design-doc.md"), "utf8");

let browser = null;
async function getBrowser() {
  if (!browser) browser = await chromium.launch();
  return browser;
}
async function closeBrowser() {
  if (browser) await browser.close();
  browser = null;
  if (server) server.close();
  server = null;
}

// The published page is wrapped in a document skeleton by claude.ai; do the same here.
let pageFile = null;
function wrappedPage() {
  if (pageFile) return pageFile;
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "readalong-"));
  pageFile = path.join(dir, "page.html");
  fs.writeFileSync(pageFile, '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>' +
    fs.readFileSync(path.join(ROOT, "page", "read-along-review.html"), "utf8") + "</body></html>");
  return pageFile;
}

// Served over http, as claude.ai serves the page over https: a file:// page's local storage is not
// reliably kept across a reload in Chromium, which made "remembered after reload" tests flaky.
let server = null, base = null;
async function baseUrl() {
  if (base) return base;
  const dir = path.dirname(wrappedPage());
  server = http.createServer((req, res) => {
    const name = path.basename(decodeURIComponent(req.url.split("?")[0])) || "page.html";
    const file = path.join(dir, name);
    if (!fs.existsSync(file)) { res.statusCode = 404; return res.end(); }
    res.setHeader("content-type", "text/html; charset=utf-8");
    res.end(fs.readFileSync(file));
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  base = `http://127.0.0.1:${server.address().port}/`;
  return base;
}

// Runs in the page before its own script.
function stands(o) {
  // Speech: utterances never end on their own; tests end them with window.__end().
  window.__spoken = [];
  Object.defineProperty(window, "speechSynthesis", {
    value: {
      speaking: false, pending: false, getVoices: () => [], addEventListener() {},
      cancel() { this.speaking = false; },
      speak(u) { this.speaking = true; window.__spoken.push(u.text); window.__last = u; },
    },
  });
  window.__end = () => window.__last && window.__last.onend && window.__last.onend();
  if (o.local) localStorage.setItem("mdr:doc", JSON.stringify(o.local));
  if (!o.db) return; // no claude.ai: the page runs in local mode

  // The page database: documents in a Map, live snapshots on every write.
  const store = new Map(Object.entries(o.db));
  window.__store = store;
  const subs = [];
  const fire = () => subs.forEach((f) => f());
  const snapDoc = (p) => ({ id: p.split("/").pop(), exists: store.has(p), data: () => store.get(p), metadata: { fromCache: false } });
  const snapCol = (col) => {
    const docs = [...store.keys()].filter((k) => k.startsWith(col + "/") && k.split("/").length === col.split("/").length + 1).map(snapDoc);
    return { docs, size: docs.length, empty: !docs.length, metadata: { fromCache: false }, docChanges: () => [] };
  };
  let n = 0;
  const docRef = (p) => ({
    path: p,
    get: async () => snapDoc(p),
    set: async (d) => { if (o.writesRefused) throw { code: "invalid_argument", message: "refused" }; store.set(p, d); fire(); },
    update: async (d) => { store.set(p, Object.assign({}, store.get(p), d)); fire(); },
    delete: async () => { store.delete(p); fire(); },
    onSnapshot(cb) { const f = () => cb(snapDoc(p)); subs.push(f); setTimeout(f, 5); return () => {}; },
  });
  const colRef = (col) => {
    const q = {
      orderBy: () => q, where: () => q, limit: () => q,
      onSnapshot(cb) { const f = () => cb(snapCol(col)); subs.push(f); setTimeout(f, 5); return () => {}; },
      doc: (id) => docRef(col + "/" + (id || "x" + ++n)),
      add: async (d) => { const id = "x" + ++n; store.set(col + "/" + id, d); fire(); return { id }; },
    };
    return q;
  };
  const db = { doc: docRef, collection: colRef };

  const user = { id: async () => "u_me", isOwner: async () => o.owner !== false };
  window.__sent = [];
  const conn = o.connector || { authStatus: "connected", tools: ["send_message"] };
  const mcp = {
    listTools: async () => ({ servers: conn.missing ? [] : [{ server: "Claude Code Remote", authStatus: conn.authStatus, tools: conn.tools.map((name) => ({ name })) }] }),
    callTool: async (server, tool, input) => { if (conn.fail) throw conn.fail; window.__sent.push({ server, tool, input }); return { payload: {} }; },
  };
  window.__permRequests = 0;
  const perms = o.permission ? {
    state: async () => window.__perm || o.permission.state,
    request: async (names) => { window.__permRequests++; window.__perm = o.permission.answer || o.permission.state; return { [names[0]]: window.__perm }; },
    manage: async () => {},
  } : null;
  const sample = o.sample != null ? async () => { await new Promise((r) => setTimeout(r, o.sampleDelay || 10)); return { text: o.sample }; } : null;
  window.claude = {
    use: async (name) => ({ db, user, mcp, permissions: perms, sample })[name] || null,
  };
}

async function open(opts = {}) {
  const b = await getBrowser();
  const context = await b.newContext({ viewport: opts.viewport || { width: 1280, height: 900 } });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.addInitScript(stands, {
    db: opts.db || null, local: opts.local || null, owner: opts.owner, connector: opts.connector, permission: opts.permission,
    sample: opts.sample == null ? null : opts.sample, sampleDelay: opts.sampleDelay, writesRefused: opts.writesRefused,
  });
  await page.goto((await baseUrl()) + "page.html");
  await page.waitForTimeout(opts.settle || 500);
  const q = (fn, arg) => page.evaluate(fn, arg);
  return {
    page, errors, q,
    spoken: () => q(() => window.__spoken.slice()),
    lastSpoken: () => q(() => window.__spoken[window.__spoken.length - 1]),
    end: async (times = 1) => { for (let i = 0; i < times; i++) { await q(() => window.__end()); await page.waitForTimeout(30); } },
    highlighted: () => q(() => { const h = CSS.highlights.get("mdr-sentence"); return h ? [...h][0].toString() : null; }),
    activeLine: () => q(() => document.querySelector(".unit.active .gutter").textContent),
    store: (key) => q((k) => window.__store && window.__store.get(k), key),
    storeKeys: (prefix) => q((p) => [...window.__store.keys()].filter((k) => k.startsWith(p)), prefix),
    say: async (text) => { await page.fill("#cmdIn", text); await page.press("#cmdIn", "Enter"); await page.waitForTimeout(120); return page.textContent("#cmdFeedback"); },
    close: () => context.close(),
  };
}

// A pull request with two files: a modified design doc with comments, and a new file.
function prFixture(extra = {}) {
  return Object.assign({
    "docs/current": {
      title: "Test PR", loadId: "o/r#7@abc", defaultFile: "f0",
      pr: { repo: "o/r", number: 7, url: "https://github.com/o/r/pull/7", headRef: "feature/x" },
      files: [{ id: "f0", path: "docs/design.md", status: "modified", changed: 3, comments: 1 }, { id: "f1", path: "docs/other.md", status: "added", changed: 3, comments: 0 }],
    },
    "files/f0": {
      path: "docs/design.md", status: "modified", markdown: SAMPLE, added: [[7, 7], [14, 14], [56, 57]], hunks: [[4, 10], [11, 17], [53, 60]],
      comments: [
        { id: "101", author: "dana", url: "https://github.com/o/r/pull/7#discussion_r1", body: "Is **2,000** still right?\n\n---\n_Generated by [Claude Code](https://claude.ai/code)_", line: 7, createdAt: "2026-11-01" },
        { id: "102", author: "ci-bot[bot]", isBot: true, body: "Lint passed", line: 7, createdAt: "2026-11-02" },
        { id: "103", author: "sam", body: "Old remark.", line: null, originalLine: 25, createdAt: "2026-10-01" },
      ],
    },
    "files/f1": { path: "docs/other.md", status: "added", markdown: "# Other\n\nNew text here. Second sentence.\n", added: [[1, 3]], hunks: [[1, 3]], comments: [] },
    "config/session": { sessionId: "session_test" },
  }, extra);
}

const SAMPLE_LOCAL = { title: "", path: "docs/rate-limiting.md", pr: "", markdown: SAMPLE };

module.exports = { open, closeBrowser, baseUrl, prFixture, SAMPLE, SAMPLE_LOCAL, wrappedPage };
