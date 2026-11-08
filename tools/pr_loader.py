#!/usr/bin/env python3
"""Prepare documents for the Read-Along Review page.

Writes one JSON file per database document into OUT_DIR:
  docs/current.json   the document set: title, pull request (if any), list of files
  files/<id>.json     one per markdown file: path, status, markdown, changed lines, review comments

Usage:
  pr_loader.py pr OWNER/REPO NUMBER OUT_DIR     markdown files changed in a pull request (needs `gh`)
  pr_loader.py repo OWNER/REPO OUT_DIR [--ref BRANCH] [--path FOLDER] [--review-pr NUMBER]
                                                markdown files in a repository, without a pull request;
                                                with --review-pr, read from that review pull request's
                                                branch, with its changes and comments
  pr_loader.py local OUT_DIR FILE.md [FILE.md]  plain markdown files, no pull request

Claude then writes these files into the page's database (ArtifactData batch with file_path).
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
from urllib.parse import quote
from datetime import datetime, timezone

MD_EXT = (".md", ".markdown", ".mdx")
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def gh(path, paginate=False):
    cmd = ["gh", "api", path]
    if paginate:
        cmd += ["--paginate", "--slurp"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"gh api {path} failed: {out.stderr.strip() or out.stdout.strip()}")
    data = json.loads(out.stdout)
    if paginate:  # --slurp wraps each page in a list
        return [item for page in data for item in page]
    return data


def ranges(lines):
    """[3,4,5,9] -> [[3,5],[9,9]]"""
    out = []
    for n in sorted(set(lines)):
        if out and n == out[-1][1] + 1:
            out[-1][1] = n
        else:
            out.append([n, n])
    return out


def parse_patch(patch):
    """New-side line numbers added by the patch, and the new-side line ranges its hunks cover."""
    added, hunks, new = [], [], 0
    for line in (patch or "").splitlines():
        m = HUNK.match(line)
        if m:
            new = int(m.group(1))
            count = int(m.group(2)) if m.group(2) is not None else 1
            if count:
                hunks.append([new, new + count - 1])
            continue
        if line.startswith("+"):
            added.append(new)
            new += 1
        elif line.startswith(" "):
            new += 1
        # "-" lines and "\ No newline" do not move the new side
    return ranges(added), hunks


def file_id(i, path):
    stem = re.sub(r"[^A-Za-z0-9_\-.]", "_", path)[-120:]
    return f"f{i}-{stem}"


def write(out_dir, rel, data):
    path = os.path.join(out_dir, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return path


def first_heading(md):
    m = re.search(r"^#{1,6}\s+(.+)$", md, re.M)
    return m.group(1).strip() if m else ""


def comment_record(c):
    on_new_side = c.get("side", "RIGHT") == "RIGHT"
    return {
        "id": str(c["id"]),
        "author": (c.get("user") or {}).get("login", ""),
        "isBot": (c.get("user") or {}).get("type") == "Bot",
        "body": c.get("body", ""),
        "line": c.get("line") if on_new_side else None,  # None: outdated, or on a deleted line
        "originalLine": c.get("original_line"),
        "inReplyTo": str(c["in_reply_to_id"]) if c.get("in_reply_to_id") else None,
        "createdAt": c.get("created_at", ""),
        "url": c.get("html_url", ""),
    }


def pr_details(repo, number):
    """The pull request, its markdown files (path -> GitHub file entry) and its review comments by path."""
    pr = gh(f"repos/{repo}/pulls/{number}")
    files = {f["filename"]: f for f in gh(f"repos/{repo}/pulls/{number}/files?per_page=100", paginate=True)
             if f["filename"].lower().endswith(MD_EXT) and f["status"] != "removed"}
    by_path = {}
    for c in gh(f"repos/{repo}/pulls/{number}/comments?per_page=100", paginate=True):
        by_path.setdefault(c.get("path"), []).append(comment_record(c))
    return pr, files, by_path


def pr_summary(repo, number, pr):
    return {
        "repo": repo, "number": int(number), "url": pr["html_url"], "title": pr["title"],
        "author": (pr.get("user") or {}).get("login", ""), "headSha": pr["head"]["sha"],
        "headRef": pr["head"]["ref"], "baseRef": pr["base"]["ref"], "state": pr["state"],
        "draft": bool(pr.get("draft")),
    }


def load_pr(repo, number, out_dir):
    pr, md_files, comments = pr_details(repo, number)
    head_sha = pr["head"]["sha"]

    index = []
    for i, (path, f) in enumerate(md_files.items()):
        content = gh(f"repos/{repo}/contents/{quote(path, safe='/')}?ref={quote(head_sha, safe='')}")
        markdown = base64.b64decode(content["content"]).decode("utf-8", errors="replace")
        patch = f.get("patch")
        added, hunks = parse_patch(patch) if patch else (None, [])
        file_comments = comments.get(path, [])
        fid = file_id(i, path)
        write(out_dir, f"files/{fid}.json", {
            "path": path,
            "status": f["status"],  # added | modified | renamed
            "markdown": markdown,
            "added": added,  # null when GitHub sent no patch (very large diffs)
            "hunks": hunks,  # line ranges a review comment may be placed on
            "comments": file_comments,
            "headSha": head_sha,
        })
        index.append({
            "id": fid, "path": path, "status": f["status"],
            "changed": sum(b - a + 1 for a, b in (added or [])),
            "comments": sum(1 for c in file_comments if not c["isBot"]),
        })

    load_id = f"{repo}#{number}@{head_sha[:12]}"
    write(out_dir, "docs/current.json", {
        "title": pr["title"],
        "pr": pr_summary(repo, number, pr),
        "files": index,
        "defaultFile": index[0]["id"] if index else None,
        "loadId": load_id,
        "loadedAt": datetime.now(timezone.utc).isoformat(),
    })
    return index


MAX_REPO_FILES = 300


def normalize_folder(path):
    path = (path or "").strip().strip("/")
    if ".." in path.split("/"):
        sys.exit("The folder must be inside the repository.")
    return path


def load_repo(repo, out_dir, ref=None, folder="", review_pr=None):
    """Markdown files of a repository (optionally one folder), read without a pull request.

    With review_pr (the draft pull request a repository review opened), the files are read from its
    branch, so they include the edits committed so far, and carry its changes and review comments."""
    folder = normalize_folder(folder)
    info = gh(f"repos/{repo}")
    ref = ref or info["default_branch"]
    pr = None
    md_changed, comments = {}, {}
    if review_pr:
        pr, md_changed, comments = pr_details(repo, review_pr)
        sha = pr["head"]["sha"]
    else:
        sha = gh(f"repos/{repo}/commits/{quote(ref, safe='')}")["sha"]
    tree = gh(f"repos/{repo}/git/trees/{sha}?recursive=1")
    prefix = folder + "/" if folder else ""
    paths = sorted(e["path"] for e in tree.get("tree", [])
                   if e.get("type") == "blob" and e["path"].lower().endswith(MD_EXT) and e["path"].startswith(prefix))
    blobs = {e["path"]: e["sha"] for e in tree.get("tree", []) if e.get("type") == "blob"}
    notes = []
    if tree.get("truncated"):
        notes.append("GitHub returned only part of this repository's file list; some files may be missing.")
    if len(paths) > MAX_REPO_FILES:
        notes.append(f"Loaded the first {MAX_REPO_FILES} of {len(paths)} markdown files; choose a folder to narrow it.")
        paths = paths[:MAX_REPO_FILES]

    index = []
    for i, path in enumerate(paths):
        blob = gh(f"repos/{repo}/git/blobs/{blobs[path]}")
        markdown = base64.b64decode(blob["content"]).decode("utf-8", errors="replace")
        f = md_changed.get(path)
        added, hunks = (parse_patch(f.get("patch")) if f and f.get("patch") else (None, [])) if f else ([], [])
        file_comments = comments.get(path, [])
        status = f["status"] if f else "unchanged"
        fid = file_id(i, path)
        write(out_dir, f"files/{fid}.json", {
            "path": path, "status": status, "markdown": markdown,
            "added": added, "hunks": hunks, "comments": file_comments, "headSha": sha,
        })
        index.append({
            "id": fid, "path": path, "status": status,
            "changed": sum(b - a + 1 for a, b in (added or [])),
            "comments": sum(1 for c in file_comments if not c["isBot"]),
        })

    name = repo + (f"/{folder}" if folder else "")
    write(out_dir, "docs/current.json", {
        "title": name,
        "pr": None,
        "repo": {
            "repo": repo, "ref": ref, "folder": folder, "sha": sha,
            "url": f"https://github.com/{repo}/tree/{quote(ref, safe='/')}" + (f"/{quote(folder, safe='/')}" if folder else ""),
        },
        "reviewPr": pr_summary(repo, review_pr, pr) if pr else None,
        "files": index,
        "defaultFile": index[0]["id"] if index else None,
        "loadId": f"{repo}@{ref}:{folder}@{sha[:12]}",
        "notes": notes,
        "loadedAt": datetime.now(timezone.utc).isoformat(),
    })
    return index, notes


def load_local(out_dir, paths):
    index = []
    for i, path in enumerate(paths):
        with open(path, encoding="utf-8") as f:
            markdown = f.read()
        fid = file_id(i, os.path.basename(path))
        write(out_dir, f"files/{fid}.json", {"path": path, "status": "local", "markdown": markdown, "added": None, "hunks": [], "comments": []})
        index.append({"id": fid, "path": path, "status": "local", "changed": 0, "comments": 0})
    with open(paths[0], encoding="utf-8") as fh:
        title = first_heading(fh.read()) or os.path.basename(paths[0])
    write(out_dir, "docs/current.json", {
        "title": title if len(paths) == 1 else f"{title} (+{len(paths) - 1} more)",
        "pr": None, "files": index, "defaultFile": index[0]["id"],
        "loadId": "local:" + "|".join(paths), "loadedAt": datetime.now(timezone.utc).isoformat(),
    })
    return index


if __name__ == "__main__":
    notes = []
    if len(sys.argv) >= 5 and sys.argv[1] == "pr":
        idx = load_pr(sys.argv[2], sys.argv[3], sys.argv[4])
    elif len(sys.argv) >= 4 and sys.argv[1] == "repo":
        ap = argparse.ArgumentParser(prog="pr_loader.py repo")
        ap.add_argument("repo"); ap.add_argument("out_dir")
        ap.add_argument("--ref"); ap.add_argument("--path", default="")
        ap.add_argument("--review-pr", type=int)
        a = ap.parse_args(sys.argv[2:])
        idx, notes = load_repo(a.repo, a.out_dir, a.ref, a.path, a.review_pr)
    elif len(sys.argv) >= 4 and sys.argv[1] == "local":
        idx = load_local(sys.argv[2], sys.argv[3:])
    else:
        sys.exit(__doc__)
    for f in idx:
        print(f"{f['id']}\t{f['status']}\t{f['changed']} changed lines\t{f['comments']} comments\t{f['path']}")
    for n in notes:
        print("NOTE: " + n)
    if not idx:
        print("No markdown files found.")
