"""Unit tests for tools/pr_loader.py and tools/post_review.py. No network: GitHub calls are replaced."""
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


loader = load("pr_loader")
post = load("post_review")

DOC = [
    "# Title",                       # 1
    "",                              # 2
    "Para one about 2,000 limits.",  # 3
    "",                              # 4
    "- item a",                      # 5
    "- item b",                      # 6
    "  more b",                      # 7
    "",                              # 8
    "Para two.",                     # 9
    "",                              # 10
    "Unchanged far away.",           # 11
]


class PatchParsing(unittest.TestCase):
    def test_added_lines_and_hunks(self):
        patch = "@@ -5,4 +5,5 @@ ctx\n \n-old\n+new\n+added\n \n x\n@@ -40,2 +41,3 @@\n a\n+b\n c\n\\ No newline at end of file"
        self.assertEqual(loader.parse_patch(patch), ([[6, 7], [42, 42]], [[5, 9], [41, 43]]))
        self.assertEqual(post.hunks_from_patch(patch), [[5, 9], [41, 43]])

    def test_new_file(self):
        self.assertEqual(loader.parse_patch("@@ -0,0 +1,3 @@\n+a\n+b\n+c"), ([[1, 3]], [[1, 3]]))

    def test_ranges(self):
        self.assertEqual(loader.ranges([3, 4, 5, 9, 4]), [[3, 5], [9, 9]])

    def test_file_ids_are_safe(self):
        self.assertEqual(loader.file_id(2, "docs/a b#c.md"), "f2-docs_a_b_c.md")


class EditingHelpers(unittest.TestCase):
    def test_replace_exact(self):
        self.assertEqual(post.replace_block(DOC, 3, 3, "2,000", "3,000"), ["Para one about 3,000 limits."])

    def test_replace_list_item_text_keeps_marker(self):
        self.assertEqual(post.replace_block(DOC, 6, 6, "item b", "item B"), ["- item B"])

    def test_replace_missing_returns_none(self):
        self.assertIsNone(post.replace_block(DOC, 3, 3, "nowhere", "x"))

    def test_marker_indentation(self):
        self.assertEqual(post.marker_line(DOC, 5), "  " + post.MARKER)
        self.assertEqual(post.marker_line(DOC, 3), post.MARKER)
        self.assertEqual(post.MARKER, "<!-- review comment -->")

    def test_apply_ops_and_line_mapping(self):
        ops = [
            (4, 3, [post.MARKER], {"source": "note"}),          # insert after line 3
            (6, 6, ["- item B!"], {"source": "edit"}),           # replace
            (9, 9, ["Para two,", "now two lines."], {"source": "edit"}),
        ]
        out, new_line, placed = post.apply_ops(DOC, ops)
        self.assertEqual(out[3], post.MARKER)
        self.assertEqual(out[6], "- item B!")
        self.assertEqual(out[9:11], ["Para two,", "now two lines."])
        self.assertEqual([new_line(n) for n in (3, 5, 7, 9, 11)], [3, 6, 8, 10, 13])

    def test_fences_outlast_inner_backticks(self):
        self.assertTrue(post.fenced("a\n```js\nx\n```", "suggestion").startswith("````suggestion\n"))
        self.assertEqual(post.fenced("plain", "suggestion"), "```suggestion\nplain\n```")

    def test_removal_suggestion_is_empty(self):
        self.assertEqual(post.removal_suggestion(), "```suggestion\n```")

    def test_revert_comment(self):
        body = post.revert_comment_body("abc1234", ["- old"])
        self.assertIn("_To **REVERT** this change, press **Commit suggestion** below._", body)
        self.assertTrue(body.endswith("```suggestion\n- old\n```"))

    def test_paths_are_encoded(self):
        self.assertEqual(post.contents_url("o/r", "docs/a#b?c%d.md"), "repos/o/r/contents/docs/a%23b%3Fc%25d.md")


class Planning(unittest.TestCase):
    """make_plan with GitHub replaced: one markdown file whose diff covers lines 1-7."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        for sub in ("notes", "edits", "docs"):
            os.makedirs(os.path.join(self.dir, sub))
        self.scope = "o/r#7:doc.md"
        self.saved = (post.pr_state, post.file_text)
        pr = {"head": {"sha": "h1", "ref": "feat", "repo": {"full_name": "o/r"}}, "base": {"repo": {"full_name": "o/r"}}, "html_url": "u"}
        post.pr_state = lambda repo, n: (pr, {"doc.md": [[1, 7]]})
        post.file_text = lambda repo, path, ref: ("\n".join(DOC), "blob")

    def tearDown(self):
        post.pr_state, post.file_text = self.saved

    def put(self, kind, id_, **data):
        with open(os.path.join(self.dir, kind, id_ + ".json"), "w") as f:
            json.dump(data, f)

    def plan(self, edit_mode="suggest", outside="summary", revert="on"):
        args = type("A", (), {"pr": ["o/r", "7"], "data": self.dir, "edit_mode": edit_mode, "outside": outside, "revert_comments": revert})
        return post.make_plan(args)

    def by_id(self, plan):
        return {a["id"]: a["do"] for a in plan["actions"]}

    def test_defaults(self):
        self.put("notes", "in", scope=self.scope, file="doc.md", line=3, endLine=3, text="in diff")
        self.put("notes", "out", scope=self.scope, file="doc.md", line=11, endLine=11, text="outside")
        self.put("edits", "e1", scope=self.scope, file="doc.md", line=6, endLine=7, original="item b", text="item B")
        self.put("edits", "e2", scope=self.scope, file="doc.md", line=9, endLine=9, original="Para two.", text="Para 2.")
        self.assertEqual(self.by_id(self.plan()), {"in": "comment", "out": "summary", "e1": "suggest", "e2": "summary"})

    def test_commit_modes(self):
        self.put("notes", "out", scope=self.scope, file="doc.md", line=11, endLine=11, text="outside")
        self.put("edits", "e1", scope=self.scope, file="doc.md", line=6, endLine=7, original="item b", text="item B")
        plan = self.plan("commit", "anchor")
        self.assertEqual(self.by_id(plan), {"out": "commit-marker", "e1": "commit"})
        self.assertEqual(plan["commitItems"], 2)
        self.assertIn("revert", post.describe(plan))
        self.assertNotIn("revert", post.describe(self.plan("commit", "anchor", "off")).split("Items:")[0])

    def test_forged_paths_and_scopes_are_skipped(self):
        self.put("edits", "evil", scope="o/r#7:.github/workflows/ci.yml", file=".github/workflows/ci.yml", line=1, endLine=1, original="x", text="y")
        self.put("notes", "liar", scope=self.scope, file="README.md", line=1, text="scope says doc.md")
        self.put("notes", "other", scope="x/y#1:doc.md", file="doc.md", line=1, text="another pull request")
        plan = self.plan("commit", "anchor")
        self.assertEqual(plan["actions"], [])
        self.assertEqual(len([w for w in plan["warnings"] if "Skipped" in w]), 2)

    def test_fork_cannot_be_committed_to(self):
        pr = {"head": {"sha": "h1", "ref": "feat", "repo": {"full_name": "someone/r"}}, "base": {"repo": {"full_name": "o/r"}}, "html_url": "u"}
        post.pr_state = lambda repo, n: (pr, {"doc.md": [[1, 7]]})
        self.put("edits", "e1", scope=self.scope, file="doc.md", line=6, endLine=7, original="item b", text="item B")
        plan = self.plan("commit", "anchor")
        self.assertEqual(self.by_id(plan), {"e1": "suggest"})
        self.assertTrue(any("fork" in w for w in plan["warnings"]))


class Executing(unittest.TestCase):
    """execute with GitHub and git replaced: checks what would be posted."""

    def setUp(self):
        self.saved = {k: getattr(post, k) for k in ("gh", "pr_state", "file_text", "commit_with_git", "wait_for_head")}
        self.posted = []
        files = {"doc.md": [[1, 7]]}

        def gh(path, method="GET", body=None, paginate=False):
            if method == "POST":
                self.posted.append(body)
                return {"html_url": "review"}
            return {"head": {"sha": "h1"}}
        post.gh = gh
        post.file_text = lambda repo, path, ref: ("\n".join(DOC), "blob")
        post.commit_with_git = lambda repo_dir, repo, plan, new_files, msg: (setattr(self, "committed", new_files), "c2")[1]
        post.wait_for_head = lambda *a, **k: None

        def state(repo, n):  # after the commit the marker after line 11 is inside a new hunk
            return {"head": {"sha": "h1"}}, {"doc.md": [[1, 7], [11, 12]]}
        post.pr_state = state

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(post, k, v)

    def run_plan(self, actions, revert=True):
        plan = {"repo": "o/r", "number": 7, "headSha": "h1", "headRef": "feat", "revertComments": revert, "actions": actions}
        path = os.path.join(tempfile.mkdtemp(), "plan.json")
        with open(path, "w") as f:
            json.dump(plan, f)
        return post.execute(path, repo_dir="/unused")

    def test_comment_marker_and_revert(self):
        res = self.run_plan([
            {"source": "note", "id": "n1", "path": "doc.md", "line": 3, "endLine": 3, "text": "in diff", "do": "comment"},
            {"source": "note", "id": "n2", "path": "doc.md", "line": 11, "endLine": 11, "text": "far", "do": "commit-marker", "marker": post.MARKER},
            {"source": "edit", "id": "e1", "path": "doc.md", "line": 6, "endLine": 7, "old": ["- item b", "  more b"], "new": ["- item B", "  more b"], "text": "item B", "do": "commit"},
        ])
        self.assertEqual(res["commits"][0]["sha"], "c2")
        self.assertIn(post.MARKER, self.committed["doc.md"])
        review = self.posted[-1]
        self.assertEqual(review["commit_id"], "c2")
        by_line = {c["line"]: c for c in review["comments"]}
        self.assertEqual(by_line[3]["body"], "in diff")
        self.assertTrue(by_line[12]["body"].startswith("far") and by_line[12]["body"].endswith(post.removal_suggestion()))
        self.assertEqual((by_line[7]["start_line"], by_line[7]["line"]), (6, 7))
        self.assertIn("**REVERT**", by_line[7]["body"])

    def test_revert_comments_off(self):
        self.run_plan([{"source": "edit", "id": "e1", "path": "doc.md", "line": 6, "endLine": 6, "old": ["- item b"], "new": ["- item B"], "text": "item B", "do": "commit"}], revert=False)
        self.assertEqual(self.posted[-1]["comments"], [])

    def test_refuses_files_outside_the_pull_request(self):
        with self.assertRaises(SystemExit):
            self.run_plan([{"source": "note", "id": "x", "path": "README.md", "line": 1, "endLine": 1, "text": "x", "do": "comment"}])


class GitCommit(unittest.TestCase):
    """commit_with_git against a local bare repository standing in for GitHub."""

    def git(self, cwd, *args):
        return subprocess.run(["git", "-C", cwd, *args], check=True, capture_output=True, text=True).stdout.strip()

    def setUp(self):
        base = tempfile.mkdtemp()
        self.origin = os.path.join(base, "o", "r.git")
        os.makedirs(self.origin)
        self.git(self.origin, "init", "--quiet", "--bare")
        seed = os.path.join(base, "seed")
        subprocess.run(["git", "clone", "--quiet", self.origin, seed], check=True, capture_output=True)
        for k, v in (("user.name", "t"), ("user.email", "t@t")):
            self.git(seed, "config", k, v)
        with open(os.path.join(seed, "doc.md"), "w") as f:
            f.write("a\nb\n")
        self.git(seed, "add", ".")
        self.git(seed, "commit", "--quiet", "-m", "seed")
        self.git(seed, "push", "--quiet", "origin", "HEAD:refs/heads/feat")
        self.head = self.git(seed, "rev-parse", "HEAD")
        self.seed = seed

    def test_fast_forward_commit(self):
        sha = post.commit_with_git(self.seed, "o/r", {"headRef": "feat", "headSha": self.head}, {"doc.md": "a\nB\n"}, "Review: 1 edit")
        self.assertEqual(self.git(self.origin, "rev-parse", "feat"), sha)
        self.assertEqual(self.git(self.origin, "show", "feat:doc.md"), "a\nB")
        self.assertEqual(self.git(self.origin, "rev-parse", "feat~1"), self.head)

    def test_refuses_when_branch_moved(self):
        with self.assertRaises(SystemExit):
            post.commit_with_git(self.seed, "o/r", {"headRef": "feat", "headSha": "0" * 40}, {"doc.md": "x"}, "m")

    def test_refuses_wrong_repository(self):
        with self.assertRaises(SystemExit):
            post.commit_with_git(self.seed, "other/repo", {"headRef": "feat", "headSha": self.head}, {"doc.md": "x"}, "m")

    def test_refuses_paths_outside_the_repository(self):
        with self.assertRaises(SystemExit):
            post.commit_with_git(self.seed, "o/r", {"headRef": "feat", "headSha": self.head}, {"../escape.md": "x"}, "m")


if __name__ == "__main__":
    unittest.main()
