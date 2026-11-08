# Working on this repository

- Behavior is specified in `docs/` (start at `docs/README.md`); a change in behavior updates those documents in the same pull request.
- A pull request that builds a feature marks it **Shipped** in the docs (with the pull request's link) in that same pull request, never "In review": once merged, it is shipped.
- The page's `<meta name="read-along-version">` must increase whenever `page/read-along-review.html` changes (CI checks it).
