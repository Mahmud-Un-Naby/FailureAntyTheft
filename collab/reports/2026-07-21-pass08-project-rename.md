# Pass 08 — Complete project rename

- Date: 2026-07-21 | Primary editor/reviewer: Codex
- Status: complete

## Scope

Apply the user-selected `FailureAntyTheft` identity consistently across the
GitHub repository, local directory, application, package, protocols, and
documentation.

## Changes

- Renamed the Python distribution and package to `failureantytheft`.
- Renamed the executable to `failureantytheft` and removed the obsolete editable
  installation.
- Renamed the service class, application state key, environment variables,
  database/export filenames, MQTT root, UI title, tests, and documentation.
- Confirmed no tracked references to the earlier names remain.
- Preserved Git history and the `origin/main` relationship.

## Validation

- Full suite: 104 passed, 1 environment-gated MQTT test skipped.
- Coverage: 84%.
- Ruff format/lint, strict mypy, and JavaScript syntax: passed.
- Renamed wheel built successfully with all HTML/CSS/JavaScript assets.
- Installed command: `failureantytheft`; obsolete command removed.

## VS Code note

The Git repository is initialized and healthy at the renamed filesystem path.
An already-open VS Code window retains the old folder URI and must be reopened
at `FailureAntyTheft` so Source Control discovers its `.git` directory.
