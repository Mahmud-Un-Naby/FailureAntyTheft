# Pass 10 — Live phone buffer compatibility

## User-visible outcome

The registered phone named **Saikat** was reachable at its Phyphox URL, but the
dashboard kept it offline because the collector expected the time buffer `t`.
The phone's live `/config` response showed that the active built-in
**Acceleration with g** experiment exposes `acc_time`, `accX`, `accY`, and
`accZ`.

The collector default has been changed from `t` to `acc_time`. Tests and setup
documentation now use the same built-in Phyphox buffer names.

## Verification evidence

- The phone returned HTTP 200 from `/config`.
- The phone reported `measuring: true`.
- A request for `acc_time`, `accX`, `accY`, and `accZ` returned all four live
  samples.
- After restarting the application, `/api/devices` reported **Saikat** as
  `disarmed` rather than `offline`, with a fresh `last_seen_at` timestamp.
- A regression test locks the collector defaults to the built-in experiment.

## Collaboration note

Claude was not involved in this pass because his earlier session limit had been
reached and the user explicitly asked Codex to continue the remaining work
alone. There was therefore no disagreement or unresolved architecture decision
between the agents in this pass.
