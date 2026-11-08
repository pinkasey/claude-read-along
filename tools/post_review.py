#!/usr/bin/env python3
"""Post a Read-Along review to its pull request, in two steps.

  post_review.py plan    --pr OWNER/REPO NUMBER --data DIR [--edit-mode suggest|commit] [--outside summary|anchor] --out PLAN.json
  post_review.py execute --plan PLAN.json --out RESULT.json

DIR holds the page's notes and edits as exported from its database: DIR/notes/*.json, DIR/edits/*.json,
and DIR/docs/current.json (to check the pull request has not moved since it was loaded).

`plan` changes nothing. It prints what would happen and writes the plan.
`execute` commits (when the plan says so) and posts one review with all the comments.

Edits on changed lines:        suggest -> suggested changes;          commit -> committed to the PR branch.
Notes/edits on unchanged lines: summary -> listed in the review body;  anchor -> committed (a marker for a note,
                                the edited text for an edit) with a review comment on it.
"""
import argparse
import base64
import glob
import json
import os
import re
import subprocess
import sys
from urllib.parse import quote

MARKER = "<!-- review note -->"
LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])(\s+)(\[[ xX]\]\s+)?")


def gh(path, method="GET", body=None, paginate=False):
    cmd = ["gh", "api", path, "-X", method]
    if paginate:
        cmd += ["--paginate", "--slurp"]
    if body is not None:
        cmd += ["--input", "-"]
    out = subprocess.run(cmd, input=json.dumps(body) if body is not None else None, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"gh api {method} {path} failed: {out.stderr.strip() or out.stdout.strip()}")
    data = json.loads(out.stdout) if out.stdout.strip() else None
    if paginate:
        return [x for page in data for x in page]
    return data


def load(dir_, col):
    out = []
    for f in sorted(glob.glob(os.path.join(dir_, col, "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        d.setdefault("id", os.path.splitext(os.path.basename(f))[0])
        out.append(d)
    return out


def hunks_from_patch(patch):
    hunks = []
    for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", patch or "", re.M):
        start, count = int(m.group(1)), int(m.group(2)) if m.group(2) is not None else 1
        if count:
            hunks.append([start, start + count - 1])
    return hunks


def pr_state(repo, number):
    pr = gh(f"repos/{repo}/pulls/{number}")
    files = gh(f"repos/{repo}/pulls/{number}/files?per_page=100", paginate=True)
    return pr, {f["filename"]: hunks_from_patch(f.get("patch")) for f in files}


def contents_url(repo, path):
    return f"repos/{repo}/contents/{quote(path, safe='/')}"  # '#', '?' and '%' in a file name are data, not URL syntax


def file_text(repo, path, ref):
    c = gh(f"{contents_url(repo, path)}?ref={quote(ref, safe='')}")
    return base64.b64decode(c["content"]).decode("utf-8"), c["sha"]


def in_one_hunk(hunks, a, b):
    return any(h[0] <= a and b <= h[1] for h in hunks)


def replace_block(lines, start, end, original, text):
    """New lines for lines[start..end] (1-based, inclusive) with `original` replaced by `text`, or None."""
    block = "\n".join(lines[start - 1:end])
    if original and original in block:
        return block.replace(original, text, 1).split("\n")
    # A list item's text is stored without its marker and indentation: match on the first line.
    first = (original or "").split("\n")[0].strip()
    if first and first in block and "\n" not in original.strip():
        return block.replace(first, text.strip(), 1).split("\n")
    return None


def marker_line(lines, start):
    line = lines[start - 1] if 0 < start <= len(lines) else ""
    m = LIST_ITEM.match(line)
    indent = len(m.group(0)) if m else len(line) - len(line.lstrip())
    return " " * indent + MARKER


def fenced(text, info=""):
    """A code fence longer than any backtick run inside, so the text cannot close it early."""
    longest = max([len(r) for r in re.findall(r"`+", text)] or [0])
    fence = "`" * max(3, longest + 1)
    return f"{fence}{info}\n{text}\n{fence}"


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


# ---------------------------------------------------------------- plan
def make_plan(a):
    repo, number = a.pr
    number = int(number)
    pr, hunks = pr_state(repo, number)
    head_sha, head_ref = pr["head"]["sha"], pr["head"]["ref"]
    same_repo = pr["head"]["repo"] and pr["head"]["repo"]["full_name"] == pr["base"]["repo"]["full_name"]
    warnings = []
    loaded = {}
    cur = os.path.join(a.data, "docs", "current.json")
    if os.path.exists(cur):
        loaded = (json.load(open(cur, encoding="utf-8")).get("pr") or {})
    if loaded.get("headSha") and loaded["headSha"] != head_sha:
        warnings.append(f"The pull request has new commits since it was loaded ({loaded['headSha'][:7]} -> {head_sha[:7]}). "
                        "Line numbers may have moved: reload it in the page and check your notes before posting.")

    prefix = f"{repo}#{number}:"
    notes = [n for n in load(a.data, "notes") if str(n.get("scope", "")).startswith(prefix)]
    edits = [e for e in load(a.data, "edits") if str(e.get("scope", "")).startswith(prefix)]
    texts = {}

    def text_of(path):
        if path not in texts:
            texts[path] = file_text(repo, path, head_sha)[0].split("\n")
        return texts[path]

    actions = []
    for n in notes:
        path, L = n["file"], int(n["line"])
        E = int(n.get("endLine") or L)
        base = {"source": "note", "id": n["id"], "path": path, "line": L, "endLine": E, "text": n["text"], "anchor": n.get("anchor", "")}
        if in_one_hunk(hunks.get(path, []), L, L):
            actions.append({**base, "do": "comment"})
        elif a.outside == "anchor":
            actions.append({**base, "do": "commit-marker", "marker": marker_line(text_of(path), L)})
        else:
            actions.append({**base, "do": "summary"})
    for e in edits:
        path, L = e["file"], int(e["line"])
        E = int(e.get("endLine") or L)
        lines = text_of(path)
        new = replace_block(lines, L, E, e.get("original", ""), e.get("text", ""))
        base = {"source": "edit", "id": e["id"], "path": path, "line": L, "endLine": E,
                "old": lines[L - 1:E], "new": new, "original": e.get("original", ""), "text": e.get("text", "")}
        if new is None:
            actions.append({**base, "do": "summary", "why": "the original text was not found at that line"})
        elif in_one_hunk(hunks.get(path, []), L, E):
            actions.append({**base, "do": "commit" if a.edit_mode == "commit" else "suggest"})
        elif a.outside == "anchor":
            actions.append({**base, "do": "commit-comment"})
        else:
            actions.append({**base, "do": "summary"})

    commit_actions = [x for x in actions if x["do"].startswith("commit")]
    if commit_actions and not same_repo:
        warnings.append("The pull request comes from a fork, so nothing can be committed to it. Committing items were changed to suggestions or the summary.")
        for x in commit_actions:
            x["do"] = "suggest" if x["do"] == "commit" else "summary"
        commit_actions = []

    committed_lines = sum(len(x["new"]) if x["source"] == "edit" else 1 for x in commit_actions)
    plan = {
        "repo": repo, "number": number, "url": pr["html_url"], "headSha": head_sha, "headRef": head_ref,
        "editMode": a.edit_mode, "outside": a.outside, "actions": actions, "warnings": warnings,
        "counts": {k: sum(1 for x in actions if x["do"] == k) for k in ["comment", "suggest", "commit", "commit-marker", "commit-comment", "summary"]},
        "commitItems": len(commit_actions), "commitLines": committed_lines,
        "commitFiles": sorted({x["path"] for x in commit_actions}),
    }
    return plan


def describe(plan):
    c = plan["counts"]
    out = [f"Review for {plan['repo']}#{plan['number']} (branch {plan['headRef']}):"]
    if c["comment"]: out.append(f"  {plural(c['comment'], 'note')} on changed lines -> review comments")
    if c["suggest"]: out.append(f"  {plural(c['suggest'], 'edit')} on changed lines -> suggested changes")
    if c["commit"]: out.append(f"  {plural(c['commit'], 'edit')} on changed lines -> committed")
    if c["commit-marker"]: out.append(f"  {plural(c['commit-marker'], 'note')} on unchanged lines -> marker committed, comment on it")
    if c["commit-comment"]: out.append(f"  {plural(c['commit-comment'], 'edit')} on unchanged lines -> committed, comment on it")
    if c["summary"]: out.append(f"  {plural(c['summary'], 'item')} -> listed in the review summary")
    if plan["commitItems"]:
        out.append(f"  Commits {plural(plan['commitItems'], 'item')} as {plural(plan['commitLines'], 'line')} "
                   f"in {', '.join(plan['commitFiles'])}")
    for w in plan["warnings"]:
        out.append("  WARNING: " + w)
    return "\n".join(out)


# ---------------------------------------------------------------- execute
def apply_ops(lines, ops):
    """ops: (start, end, new_lines, action); replaces lines[start..end] (1-based; end = start - 1 inserts).
    Returns new lines and a function mapping an old line number to its new one."""
    ops = sorted(ops, key=lambda o: (o[0], o[1]))
    out, delta, placed = list(lines), 0, []
    for start, end, new, act in ops:
        s = start - 1 + delta
        out[s:s + (end - start + 1)] = new
        placed.append((start, end, start + delta, len(new), act))
        delta += len(new) - (end - start + 1)

    def new_line(old):
        shift = 0
        for start, end, new_start, n_new, _ in placed:
            if start <= old <= end:
                return new_start + (old - start)
            if end < old:
                shift += n_new - (end - start + 1)
        return old + shift
    return out, new_line, placed


def execute(plan_path):
    plan = json.load(open(plan_path, encoding="utf-8"))
    repo, number = plan["repo"], plan["number"]
    pr = gh(f"repos/{repo}/pulls/{number}")
    if pr["head"]["sha"] != plan["headSha"]:
        raise SystemExit("The pull request changed since the plan was made. Make a new plan.")
    actions = plan["actions"]
    head = plan["headSha"]
    mapping, commits = {}, []

    by_path = {}
    for x in actions:
        if x["do"] in ("commit", "commit-comment"):
            by_path.setdefault(x["path"], []).append((x["line"], x["endLine"], x["new"], x))
        elif x["do"] == "commit-marker":
            by_path.setdefault(x["path"], []).append((x["endLine"] + 1, x["endLine"], [x["marker"]], x))
    for path, ops in by_path.items():
        text, sha = file_text(repo, path, plan["headSha"])
        new_lines, new_line, placed = apply_ops(text.split("\n"), ops)
        mapping[path] = new_line
        for start, end, new_start, n_new, act in placed:
            act["newLine"], act["newEndLine"] = new_start, new_start + max(n_new, 1) - 1
        n_edit = sum(1 for o in ops if o[3]["source"] == "edit")
        n_note = len(ops) - n_edit
        msg = "Review: " + ", ".join(p for p in [plural(n_edit, "edit") if n_edit else "", plural(n_note, "note marker") if n_note else ""] if p)
        msg += f" in {path}\n\nCommitted from a Read-Along review of #{number}."
        if os.environ.get("READALONG_COMMIT_TRAILER"):  # attribution lines, supplied by the session that posts
            msg += "\n\n" + os.environ["READALONG_COMMIT_TRAILER"]
        res = gh(contents_url(repo, path), "PUT", {
            "message": msg, "branch": plan["headRef"], "sha": sha,
            "content": base64.b64encode("\n".join(new_lines).encode("utf-8")).decode("ascii"),
        })
        head = res["commit"]["sha"]
        commits.append({"path": path, "sha": head, "url": res["commit"]["html_url"]})

    # Comments, on the lines as they are after the commits.
    _, hunks = pr_state(repo, number) if commits else (None, None)
    comments, summary_items, failed = [], [], []
    for x in actions:
        nl = mapping.get(x["path"], lambda v: v)
        if x["do"] == "comment":
            line = nl(x["line"])
            comments.append({"x": x, "c": {"path": x["path"], "line": line, "side": "RIGHT", "body": x["text"]}})
        elif x["do"] == "suggest":
            a, b = nl(x["line"]), nl(x["endLine"])
            c = {"path": x["path"], "line": b, "side": "RIGHT", "body": fenced("\n".join(x["new"]), "suggestion")}
            if b > a:
                c.update(start_line=a, start_side="RIGHT")
            comments.append({"x": x, "c": c})
        elif x["do"] == "commit-marker":
            comments.append({"x": x, "c": {"path": x["path"], "line": x["newLine"], "side": "RIGHT", "body": x["text"]}})
        elif x["do"] == "commit-comment":
            short = commits[-1]["sha"][:7] if commits else ""
            body = f"Edited during review (committed in {short}). It was:\n\n" + fenced("\n".join(x["old"]), "markdown")
            c = {"path": x["path"], "line": x["newEndLine"], "side": "RIGHT", "body": body}
            if x["newEndLine"] > x["newLine"]:
                c.update(start_line=x["newLine"], start_side="RIGHT")
            comments.append({"x": x, "c": c})
        elif x["do"] == "summary":
            summary_items.append(x)
    if hunks is not None:  # after commits, check each comment still lands inside the diff
        kept = []
        for item in comments:
            c = item["c"]
            if in_one_hunk(hunks.get(c["path"], []), c.get("start_line", c["line"]), c["line"]):
                kept.append(item)
            else:
                failed.append(item["x"])
        comments = kept
        summary_items += failed

    body = ["Review notes from a Read-Along listening review."]
    if commits:
        body.append("\n**Committed during review**")
        body += [f"- `{c['path']}`: {c['url']}" for c in commits]
    if summary_items:
        body.append("\n**Notes and edits on lines outside the diff**")
        for x in summary_items:
            if x["source"] == "note":
                body.append(f"- `{x['path']}` line {x['line']}: {x['text']}" + (f"\n  > {x['anchor']}" if x.get("anchor") else ""))
            else:
                why = f" ({x['why']})" if x.get("why") else ""
                body.append(f"- `{x['path']}` line {x['line']}, suggested edit{why}:\n\n  "
                            + fenced(x["text"] or "", "markdown").replace("\n", "\n  "))
    review = gh(f"repos/{repo}/pulls/{number}/reviews", "POST", {
        "commit_id": head, "event": "COMMENT", "body": "\n".join(body), "comments": [i["c"] for i in comments],
    })
    return {
        "review": review.get("html_url"), "commits": commits,
        "posted": sorted({x["id"] + "|" + x["source"] for x in actions}),
        "commentCount": len(comments), "summaryCount": len(summary_items),
        "movedToSummary": [x["id"] for x in failed],
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--pr", nargs=2, required=True, metavar=("OWNER/REPO", "NUMBER"))
    p.add_argument("--data", required=True)
    p.add_argument("--edit-mode", choices=["suggest", "commit"], default="suggest")
    p.add_argument("--outside", choices=["summary", "anchor"], default="summary")
    p.add_argument("--out", required=True)
    x = sub.add_parser("execute")
    x.add_argument("--plan", required=True)
    x.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "plan":
        plan = make_plan(a)
        json.dump(plan, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(describe(plan))
    else:
        res = execute(a.plan)
        json.dump(res, open(a.out, "w", encoding="utf-8"), indent=1)
        print(json.dumps(res, indent=1))
