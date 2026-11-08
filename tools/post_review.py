#!/usr/bin/env python3
"""Post a Read-Along review to its pull request, in two steps.

  post_review.py plan    --pr OWNER/REPO NUMBER --data DIR [--edit-mode suggest|commit] [--outside summary|anchor] --out PLAN.json
  post_review.py execute --plan PLAN.json --out RESULT.json [--repo-dir CLONE]

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
import tempfile
import time
from urllib.parse import quote

MARKER = "<!-- review note -->"
MD_EXT = (".md", ".markdown", ".mdx")
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
    """The pull request, and the diff ranges of the markdown files it adds or changes.
    Only these files may be commented on or committed to: a path stored with a note or edit is
    never trusted on its own."""
    pr = gh(f"repos/{repo}/pulls/{number}")
    files = gh(f"repos/{repo}/pulls/{number}/files?per_page=100", paginate=True)
    return pr, {f["filename"]: hunks_from_patch(f.get("patch")) for f in files
                if f["filename"].lower().endswith(MD_EXT) and f["status"] != "removed"}


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


def removal_suggestion():
    """A suggested change with no lines: applying it deletes the commented line."""
    return "```suggestion\n```"


def revert_comment_body(commit_short, old_lines):
    """The comment on an edit committed during review: says so, and offers a one-click revert
    (a suggested change that puts the original lines back)."""
    return (f"Edited during review (committed in {commit_short}).\n\n"
            "_To **REVERT** this change, press **Commit suggestion** below._\n\n"
            + fenced("\n".join(old_lines), "suggestion"))


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
    refused = [x for x in notes + edits if x.get("file") not in hunks or x.get("scope") != prefix + str(x.get("file"))]
    for x in refused:
        warnings.append(f"Skipped an item for {x.get('file')!r}: it is not a markdown file changed by this pull request.")
    notes = [n for n in notes if n not in refused]
    edits = [e for e in edits if e not in refused]
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
    labels = {"comment": "comment", "suggest": "suggested change", "commit": "commit",
              "commit-marker": "commit marker + comment", "commit-comment": "commit + comment", "summary": "summary"}
    out.append("Items:")
    for x in sorted(plan["actions"], key=lambda x: (x["path"], x["line"])):
        what = x["text"] if x["source"] == "note" else ("-> " + " / ".join(x["new"]) if x.get("new") else x["text"])
        out.append(f"  [{labels[x['do']]}] {x['path']}:{x['line']} {x['source']}: {what}")
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


def git(repo_dir, *args, input=None):
    out = subprocess.run(["git", "-C", repo_dir, *args], input=input, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {out.stderr.strip() or out.stdout.strip()}")
    return out.stdout.strip()


def commit_with_git(repo_dir, repo, plan, new_files, msg):
    """One commit on the pull request branch, made on top of exactly the planned head, pushed as a
    fast-forward (never forced: if the branch moved, the push is refused)."""
    origin = git(repo_dir, "remote", "get-url", "origin")
    if not re.search(rf"[/:]{re.escape(repo)}(\.git)?$", origin):
        raise SystemExit(f"{repo_dir} is a clone of {origin}, not {repo}.")
    branch = plan["headRef"]
    git(repo_dir, "fetch", "--quiet", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}")
    if git(repo_dir, "rev-parse", f"refs/remotes/origin/{branch}") != plan["headSha"]:
        raise SystemExit(f"{branch} has new commits since the plan was made. Make a new plan.")
    work = tempfile.mkdtemp(prefix="readalong-")
    git(repo_dir, "worktree", "add", "--quiet", "--detach", work, plan["headSha"])
    try:
        for path, text in new_files.items():
            full = os.path.join(work, path)
            if os.path.commonpath([os.path.realpath(full), os.path.realpath(work)]) != os.path.realpath(work):
                raise SystemExit(f"Refusing a path outside the repository: {path}")
            with open(full, "w", encoding="utf-8", newline="") as f:
                f.write(text)
            git(work, "add", "--", path)
        git(work, "commit", "--quiet", "-F", "-", input=msg)
        git(work, "push", "--quiet", "origin", f"HEAD:refs/heads/{branch}")
        return git(work, "rev-parse", "HEAD")
    finally:
        subprocess.run(["git", "-C", repo_dir, "worktree", "remove", "--force", work], capture_output=True)


def wait_for_head(repo, number, sha, tries=15):
    """GitHub updates a pull request's head shortly after a push; comments need the new head."""
    for _ in range(tries):
        if gh(f"repos/{repo}/pulls/{number}")["head"]["sha"] == sha:
            return
        time.sleep(2)
    raise SystemExit(f"Committed {sha[:7]} to the branch, but the pull request did not show it yet, so no comments were posted. "
                     "Make a new plan from the notes that were not posted (the committed items are already on the branch).")


def execute(plan_path, repo_dir=None):
    plan = json.load(open(plan_path, encoding="utf-8"))
    repo, number = plan["repo"], plan["number"]
    pr = gh(f"repos/{repo}/pulls/{number}")
    if pr["head"]["sha"] != plan["headSha"]:
        raise SystemExit("The pull request changed since the plan was made. Make a new plan.")
    _, allowed = pr_state(repo, number)
    stray = sorted({x["path"] for x in plan["actions"] if x["path"] not in allowed})
    if stray:  # the plan file was changed, or the pull request's files changed: refuse rather than guess
        raise SystemExit(f"The plan names files this pull request does not change: {', '.join(stray)}. Make a new plan.")
    actions = plan["actions"]
    head = plan["headSha"]
    mapping, commits = {}, []

    by_path = {}
    for x in actions:
        if x["do"] in ("commit", "commit-comment"):
            by_path.setdefault(x["path"], []).append((x["line"], x["endLine"], x["new"], x))
        elif x["do"] == "commit-marker":
            by_path.setdefault(x["path"], []).append((x["endLine"] + 1, x["endLine"], [x["marker"]], x))
    new_files, blob_shas = {}, {}
    for path, ops in by_path.items():
        text, sha = file_text(repo, path, plan["headSha"])
        new_lines, new_line, placed = apply_ops(text.split("\n"), ops)
        mapping[path] = new_line
        for start, end, new_start, n_new, act in placed:
            act["newLine"], act["newEndLine"] = new_start, new_start + max(n_new, 1) - 1
        new_files[path], blob_shas[path] = "\n".join(new_lines), sha
    if new_files:
        ops_all = [o for ops in by_path.values() for o in ops]
        n_edit = sum(1 for o in ops_all if o[3]["source"] == "edit")
        n_note = len(ops_all) - n_edit
        msg = "Review: " + ", ".join(p for p in [plural(n_edit, "edit") if n_edit else "", plural(n_note, "note marker") if n_note else ""] if p)
        msg += f"\n\nCommitted from a Read-Along review of #{number}:\n" + "\n".join(f"- {p}" for p in sorted(new_files))
        if os.environ.get("READALONG_COMMIT_TRAILER"):  # attribution lines, supplied by the session that posts
            msg += "\n\n" + os.environ["READALONG_COMMIT_TRAILER"]
        if repo_dir:
            head = commit_with_git(repo_dir, repo, plan, new_files, msg)
            commits.append({"path": ", ".join(sorted(new_files)), "sha": head, "url": f"https://github.com/{repo}/commit/{head}"})
        else:
            for path, text in new_files.items():  # the contents API makes one commit per file
                res = gh(contents_url(repo, path), "PUT", {
                    "message": msg, "branch": plan["headRef"], "sha": blob_shas[path],
                    "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
                })
                head = res["commit"]["sha"]
                commits.append({"path": path, "sha": head, "url": res["commit"]["html_url"]})
        wait_for_head(repo, number, head)

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
            body = x["text"] + "\n\n<sub>This line is a marker committed during review so this comment could be placed here. " \
                               "Commit the suggestion below to remove it.</sub>\n\n" + removal_suggestion()
            comments.append({"x": x, "c": {"path": x["path"], "line": x["newLine"], "side": "RIGHT", "body": body}})
        elif x["do"] == "commit-comment":
            short = commits[-1]["sha"][:7] if commits else ""
            body = revert_comment_body(short, x["old"])
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
    x.add_argument("--repo-dir", help="a local clone of the repository: commit with git (fetch, commit, push) instead of the contents API")
    a = ap.parse_args()
    if a.cmd == "plan":
        plan = make_plan(a)
        json.dump(plan, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(describe(plan))
    else:
        res = execute(a.plan, a.repo_dir)
        json.dump(res, open(a.out, "w", encoding="utf-8"), indent=1)
        print(json.dumps(res, indent=1))
