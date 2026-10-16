# Low-token long-run monitoring policy

## Default architecture

1. The local monitor owns high-frequency supervision:
   - poll every 5 seconds;
   - write a compact status heartbeat every 120 seconds;
   - stop only after 20 minutes with neither log growth nor progress;
   - extend the emergency ceiling while progress remains active.
2. Codex does not mirror the local heartbeat.
3. If a thread heartbeat is needed, schedule it every 30 minutes by default.
4. Healthy checks remain silent. Notify only on:
   - completed stage;
   - failed or stalled stage;
   - parameter/output drift;
   - a decision that requires user authority.
5. Read `monitor_attention.json` first. Read full status or log tails only when
   that compact event says `completed` or `attention_required`.

## Required entry point

Use:

`python -m monitor_kwave_process`

The module entry is stage-aware:

- `calibrate` expects `element_signals.npz` and `summary_calibrate.json`;
- `refocus` expects `pressure_max_mpa.npz`, `summary.json`, and
  `focus_metrics.json`;
- tqdm progress accepts both `s/step` and `step/s`.

The legacy script entry remains preserved for traceability.

## Token budget rule

Do not create five-minute Codex heartbeats for a healthy long simulation.
Prefer one check near the conservative ETA or a 30-minute silent heartbeat.
The local monitor provides safety between model wakeups without consuming
conversation tokens.
