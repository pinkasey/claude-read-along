# Repositories

Status: **In review**

Reading the markdown of a repository, or one folder of it, without a pull request. The reviewer may only decide to propose changes while listening; the review pull request is created when they first post.

## Opening a repository

The reviewer either:

- presses **Open PR or repo** in the page and enters a repository: `OWNER/REPO`, optionally with `@BRANCH` and `:FOLDER` (`owner/repo@dev:docs/specs`), or a GitHub link to the repository or to a folder (`https://github.com/OWNER/REPO/tree/BRANCH/FOLDER`), then **Ask Claude to load it**, or
- tells Claude in the chat which repository or folder to read.

The page rejects paths containing `..`. Without a branch, the repository's default branch is used; without a folder, the whole repository.

Claude runs `tools/pr_loader.py repo`, which reads every markdown file under the folder at the branch's current commit (at most 300 files; when there are more, Claude says so). The files load as unchanged: there are no change markers and no review comments. The header shows the repository and branch, linked to the folder on GitHub.

## Comments and edits

Comments and edits work as in a pull request ([comments-and-edits.md](comments-and-edits.md)). They are scoped to `OWNER/REPO@BRANCH:<path>`, and that scope stays the same after the review pull request exists, so nothing is lost when it is created.

## Posting: the review pull request

The first **Post review** for a repository:

1. creates a branch `read-along/review-<time>` from the branch being read,
2. commits there the edits, and the markers for comments (every line is outside a diff, since there is no pull request yet),
3. opens a **draft** pull request from that branch, titled "Review of FOLDER (BRANCH)",
4. posts the comments on the committed lines, as in [posting-reviews.md](posting-reviews.md).

Rules:

- A pull request needs at least one commit. With the setting **Comments and edits on unchanged lines** set to summary, or with nothing to commit, the page explains this and its **Post review** button is disabled; Claude refuses the plan too (`CANNOT POST`).
- Claude asks first: "Create branch BRANCH from BASE in OWNER/REPO, commit X edits as Y lines, and open a draft pull request with your comments?" with **Create the pull request** and **Don't post**.
- The branch must not exist yet, and the base branch must still be at the commit the plan was made from; otherwise nothing is posted.
- Only markdown files under the folder that was read can be committed to.

After posting, the page header links "review PR #N (draft)". Claude reloads the review from the pull request's branch, so the committed changes and the posted comments show, and files not reached yet are still there. Later posts go to the same pull request, with the usual settings and confirmation. The reviewer marks the pull request ready for review on GitHub when they want to.
