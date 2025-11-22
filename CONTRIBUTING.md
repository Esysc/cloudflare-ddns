# Contributing

Thanks for your interest in contributing to this project — we welcome improvements, bug
fixes, documentation updates, tests, and ideas. This document explains the most
common ways to contribute and the project's expectations for contributions.

## Table of content

- **Getting started**
- **Reporting issues**
- **Proposing changes (Pull Requests)**
- **Branching & commit guidance**
- **Code style & tests**
- **Pre-commit hooks & CI**
- **Security & sensitive data**
- **Code of conduct**

## Getting started

- Fork the repository on GitHub to your account.
- Clone your fork locally and add the upstream remote (the original repo):

  ```bash
  git clone git@github.com:<your-username>/cloudflare-ddns.git
  cd cloudflare-ddns
  git remote add upstream git@github.com:Esysc/cloudflare-ddns.git
  git fetch upstream
  ```

- Create a feature branch for your change (describe the change in the branch name):

  ```bash
  git checkout -b fix/update-contributing-doc
  ```

## Reporting issues

- If you found a bug, missing behavior, or have a feature idea, open an issue in the
  upstream repository. Provide a minimal reproduction, expected vs actual behavior,
  and environment details (OS, Python version, steps to reproduce).

## Proposing changes (Pull Requests)

- Make changes on a branch in your fork, commit, and push the branch to your fork:

  ```bash
  git add CONTRIBUTING.md
  git commit -m "docs: improve contributing guide"
  git push origin fix/update-contributing-doc
  ```

- Open a Pull Request from your fork/branch to the upstream branch (`bugfix/fixes1` or `main` as appropriate).
- In the PR description, include:
  - Summary of the change
  - Why it's needed
  - Any testing you performed
  - Any migration or breaking changes

- Keep changes focused and small where possible. Large or complex changes are easier
  to review when split into smaller PRs.

## Branching & commit guidance

- Create short-lived branches for each logical change.
- Use clear commit messages. Follow this pattern for the first line:

  ```text
  <type>(<scope>): <short summary>

  e.g. "fix(ddns): preserve record TTL when updating"
  ```

- Types commonly used: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`.

## Code style & tests

- The project uses lightweight linting and formatting tools in pre-commit.
- Keep functions small and add docstrings for public functions.
- When you add functionality, include or update tests in `tests/` that exercise
  the behavior. Unit tests should not make network calls; use mocking for HTTP.

## Pre-commit hooks & CI

- This repo includes a `.pre-commit-config.yaml`. Please run and satisfy the
  pre-commit checks locally before opening a PR:

  ```bash
  pip install -r requirements-dev.txt
  pre-commit install
  pre-commit run --all-files
  ```

- The CI workflow runs tests on push/PR. Ensure your changes pass CI before requesting review.

## Security & sensitive data

- Do not commit secrets, API tokens, or credentials. Use environment variables
  or GitHub Secrets for CI.
- If you discover a security issue, do not open a public issue. Instead contact
  the maintainers (or the repository owner) privately so the issue can be
  investigated and handled appropriately.

## Code of Conduct

- Be respectful, helpful, and collaborative. Report unacceptable behavior to the
  maintainers. This project follows a standard code of conduct; by participating
  you agree to be welcoming and professional.

## Maintainers & review process

- Maintainers will review PRs and may request changes. Small PRs can be merged
  quickly; larger changes may take longer.
- If your PR needs more work, please address feedback and push follow-up commits
  to the same branch.

## Useful commands

```bash
# keep fork up to date with upstream
git fetch upstream
git checkout main
git merge upstream/main

# create branch from updated main
git checkout -b my-feature-branch

# commit and push
git add .
git commit -m "feat: ..."
git push origin my-feature-branch
```

Thank you for considering a contribution — your help makes this project better!
