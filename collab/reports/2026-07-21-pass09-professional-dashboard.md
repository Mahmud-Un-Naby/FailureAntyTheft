# Pass 09 — Professional dashboard redesign

- Date: 2026-07-21 | Primary editor/reviewer: Codex
- Status: complete

## Scope

Replace the prototype-style dashboard with a professional, responsive security
console while preserving the validated API, WebSocket, and detector behavior.

## Changes

- Added a structured desktop sidebar and compact mobile navigation.
- Added system health and live-channel indicators, local time, protection
  summary metrics, global controls, and clear empty states.
- Rebuilt device cards with operational state, motion score, endpoint,
  sensitivity, contact time, live selection, arm/disarm, and edit controls.
- Added an accessible add/edit sensor dialog with validation guidance,
  sensitivity control, and enabled-state management.
- Rebuilt the live chart for responsive high-DPI rendering and accurate
  online/offline/waiting states.
- Reworked event history with filters, readable severity/status badges,
  acknowledgement actions, and CSV export.
- Added persistent alarm handling, browser notifications when permitted,
  audible alerts, reconnect feedback, mobile layouts, toasts, keyboard focus,
  reduced-motion support, and semantic labels.

## Validation

- Desktop 1440×1100 Chrome render: visually reviewed.
- Mobile 390×844 Chrome render: visually reviewed; no horizontal overflow in
  the primary workflow.
- JavaScript syntax, Ruff format/lint, and strict mypy: passed.
- Full backend/UI regression suite: 104 passed, 1 environment-gated MQTT test
  skipped.
- Static dashboard HTML, CSS, and JavaScript delivery now has API regression
  assertions.
