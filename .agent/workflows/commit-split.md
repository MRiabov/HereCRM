---
description: Commit changes in individual commits.
---

Split git status by meaning and commit it.
When doing commit names, I use the following rules:
Rules that I use:
(spec) - for editing markdown files, in particular spec-kitty files.
(refactor) - refactoring; no user-facing changes were done but internally we refactored code.
(debug) - debug the code.
(test) - add test coverage/fix existing ones.
(devops) - editing Kubernetes, vercel, etc files.

Any UI or backend (user-facing features) are not prefixed.

Examples of commit names:

- (spec) Specified spec 025 (when edited spec.md at spec 025)
- (refactor) Make webhook logic more modular
- (debug) fix the test failure at [...]
