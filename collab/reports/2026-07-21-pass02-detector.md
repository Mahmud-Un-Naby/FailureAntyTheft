# Pass 02 — Pure movement detector

- Stage: 1 | Date: 2026-07-21 | Primary editor/reviewer: Codex
- Status: consensus unavailable — completed under the user-authorized Claude-limit fallback

## 1. Understanding

Implement deterministic movement and state-machine behavior without I/O. The
later runtime supplies commands, link changes, samples, and monotonic time.

## 2. Scope

In scope: placement delay, calibration, variance rejection, EMA filtering,
sustained threshold crossings, alarm/disarm behavior, offline recovery, stale
sample rejection, and unit tests. Database, bus, API, and phone access remain
out of scope.

## 3. Changes

- Added `failurealert.detection.detector` and package exports.
- Added deterministic detector tests covering success and failure paths.

## 4. Contracts

No shared wire contract changed. Detector inputs/outputs are internal frozen
dataclasses. Phyphox experiment time controls the crossing window; supplied
monotonic time controls calibration timers.

## 5. Validation

```text
pytest: 83 passed in 0.40s
ruff check: All checks passed
ruff format --check: 9 files already formatted
mypy: Success, 6 source files
```

## 6. Cross-review

Claude was unavailable due to its previously reported session limit. Codex
performed implementation, failure-path review, and automated validation. This
report does not claim Claude consensus.

## 7. Open items for the user

None requiring a decision. Real-phone threshold values remain intentionally
unfrozen until physical fixtures are available.

## 8. Next pass

Implement the in-process bus, SQLite repository, and `DeviceRuntime` wrapper.
