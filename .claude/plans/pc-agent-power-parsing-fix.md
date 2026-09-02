# Plan: Fix pc-agent power parsing for LibreHardwareMonitor string RawValues

## Problem

`_walk_lhm()` drops every Power sensor because LHM serializes `RawValue` as a
formatted string with units (`"41.5 W"`), and the Power branch does `float(RawValue)`
with a silent `except`. Temperature works because `_lhm_celsius` has a string fallback.

## Change

In `services/monitoring/pc-agent/agent.py`:

1. Add a small parser `_lhm_number(node)` that:
   - tries `float(node.get("RawValue"))`
   - on failure, parses the numeric prefix of `node.get("Value", "")` (strip units,
     handle locale comma, like `_lhm_celsius`)
   - returns `None` on failure or non-finite values.

2. In `_walk_lhm()`, replace the Power branch's raw `float()` with:
   - `power_val = _lhm_number(node)`; append only when `> 0`.

3. Optionally refactor `_lhm_celsius` to use the same helper (keeps one parsing path) —
   verify it remains behavior-identical for temperature.

No metric-name, label, or dashboard changes. No new dependencies.

## Verification

- `python3 agent.py --dry-run` on Halo (no-op for platform) — not applicable on Linux,
  so verify via: unit-style check of `_lhm_number` on `"41.5 W"`, `42`, `""`, `None`.
- On the remote: `git pull && python3 bootstrap.py` (using the venv interpreter),
  then confirm from the Halo that the pushgateway group gains `node_power_watts` for
  `Cracked-ITX` and Prometheus `node_power_watts{job="pc_agent"}` is non-empty.
- Confirm `Device Aggregate` — Power Detail panels show Cracked-ITX alongside Halo.

## Out of scope

- Linux sysfs power (`/sys/class/power_supply/power_now`) — verify it still passes the
  existing unit division (`1e6`) unchanged.
- Dashboard/query changes.