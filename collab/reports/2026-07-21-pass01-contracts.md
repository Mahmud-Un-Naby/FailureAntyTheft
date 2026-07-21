# Pass 01 — Executable contracts

- Stage: 0 | Date: 2026-07-21 | Primary editor: Claude, completed by Codex after Claude's session limit | Reviewer: Codex
- Status: completed-by-Codex — Claude retrospective review unavailable because its limit resets at 11:40 PM Asia/Dhaka

## 1. What Claude understood

Claude correctly understood this pass as a bounded contract freeze: create the
Python package metadata, strict Pydantic message/persistence models, validated
topic helpers, signature-only bus/repository ports, and contract tests. It kept
detector, runtime, database implementation, collector, API, dashboard, and MQTT
implementation out of scope.

Claude also confirmed before editing that it had no limit warning and enough
capacity for the bounded pass. It inspected `ARCHITECTURE.md` and
`collab/DECISIONS.md`, raised four contract questions, and waited for Codex to
resolve them before editing.

## 2. Scope of this pass

In scope:

- Python package and development-tool configuration;
- strict, frozen, versioned bus and WebSocket contracts;
- minimal persistence records needed by the repository protocol;
- MQTT-safe topic construction and parsing;
- signature-only `Bus` and `Repo` protocols; and
- tests for serialization, validation, invariants, and topics.

Explicitly out of scope: executable detector/runtime/repository/bus behavior,
Phyphox collection, API/WS routes, dashboard, Mosquitto, and physical-phone
fixtures.

## 3. What changed

Claude initially created:

- `pyproject.toml` and `.gitignore`;
- `src/failureantytheft/__init__.py`;
- `src/failureantytheft/contracts.py`;
- `src/failureantytheft/topics.py`;
- `src/failureantytheft/ports.py`;
- `tests/test_contracts.py`; and
- `tests/test_topics.py`.

Codex then completed the pass after cross-review by fixing lint/type failures and
adding invariants for command device identity, retained-status timestamps,
link/state consistency, alert metrics, acknowledgement metadata, transport
status, positive thresholds/sensitivity, whitespace-only identifiers, and exact
topic-ID matching.

The local `.venv` was created and the editable project plus development
dependencies were installed. `.venv` is ignored by Git.

## 4. Contracts touched

This pass created the executable v1 contracts described by `ARCHITECTURE.md`.
Every bus/WS payload carries `schema_version=1`. Device time is represented as
nonnegative experiment-relative seconds; server timestamps must be timezone
aware. `Command` includes `device_id` as well as topic routing identity so a
runtime can reject mismatches.

## 5. Validation

The first Codex gate produced real failures:

- `pytest -q`: **56 passed**;
- `ruff check .`: **failed**, one unsorted import block; and
- `mypy`: **failed**, `CONTRACTS_VERSION` was typed as `int` where `Literal[1]`
  was required.

After the corrections, the final gate was:

```text
.venv/bin/python -m pytest -q
68 passed in 0.31s

.venv/bin/python -m ruff check .
All checks passed!

.venv/bin/python -m ruff format --check .
6 files already formatted

.venv/bin/python -m mypy
Success: no issues found in 4 source files
```

Dependency installation initially failed because sandbox DNS was unavailable,
then succeeded through the user-authorized network installation path.

## 6. Cross-review

Claude performed the initial implementation and a static self-review, but its
terminal required approval for every validation command. Codex ran the gate and
found the two failures above plus missing domain invariants. When Codex sent the
bounded correction list back, Claude's CLI returned:

```text
You've hit your session limit · resets 11:40pm (Asia/Dhaka)
```

Per the user's explicit fallback instruction, Codex applied the corrections and
reran the complete gate. This report does **not** claim final Claude/Codex
consensus on those corrections; Claude was unavailable for the final review.

## 7. Open items for the user

- Claude reached its session limit and cannot continue this session. The user
  asked to continue the remaining work with Codex in this situation.
- Claude may retrospectively review this pass after its limit resets, but that is
  optional and does not block Codex under the user's fallback instruction.
- Physical Phyphox output still must be confirmed later using the user's phones;
  no contract claims that the currently available phones expose a particular
  buffer name.

## 8. Next proposed pass

Implement the pure detector and its state-machine tests first. Keep I/O in a
later runtime wrapper so the movement algorithm remains deterministic and
replayable.
