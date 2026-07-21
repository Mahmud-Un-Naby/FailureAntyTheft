# Pass 11 — Audible browser alarm

## User-visible outcome

The dashboard now plays a repeating two-tone siren while a movement alert is
active. Arming a device prepares browser audio during the operator's click, so
the browser's autoplay policy does not silently block the later alarm.

The header provides a clear **Sound on/off** control that plays a test tone when
enabled. The active alarm banner also provides an immediate enable/mute control.
Acknowledging the alert, disarming it, or muting sound stops the siren.

## Reliability improvements

- Active movement alerts restored from event history restart the siren when
  audio is enabled.
- Only one repeating timer may run, even when polling and WebSocket messages
  report the same alert.
- An explicit mute choice is respected when devices are armed afterward.
- Browser notifications remain optional and are requested only from the
  operator's explicit sound-control click.

## Collaboration note

Claude was not involved because his earlier session limit had been reached and
the user asked Codex to continue independently. No cross-agent disagreement is
open for this pass.
