# Technical Analysis: pc-agent Pushes No Power Metrics (Windows/LHM)

## 1. Executive Summary

The power-monitoring feature added in `c760f75` emits `node_power_watts` from the
pc-agent, but **zero power series** show up for `job="pc_agent"` devices. The
`Device Aggregate` dashboard's "Power Detail" section (`node_power_watts{instance=~"$device}"`)
is permanently empty, so only the Halo's own `node_hwmon_power_watt` (node_exporter)
plots on the aggregate power graphs.

Verified against the live stack:

```
# no power series exist anywhere for the remote device:
node_power_watts                          => (empty)
{job="pc_agent"}                          => cpu/mem/disk/network/load/temp all present, no power

# the device does NOT lack power sensors — LHM reports them:
GET http://cracked-itx:8085/data.json
  Power | Package         41.5 W      (AMD Ryzen 7 9800X3D)
  Power | Core #1..8 (SMU) 1.7-5.3 W  (Ryzen SMU per-core)
  Power | GPU Package     43.9 W      (NVIDIA GeForce RTX 5080)
```

## 2. Root Cause

`_walk_lhm()` in `services/monitoring/pc-agent/agent.py` handles Power-type nodes as:

```python
elif node_type == "Power":
    try:
        power_val = float(node.get("RawValue", 0))   # <-- fails
        if power_val > 0:
            out.append((chip or "lhm", name, power_val, "power"))
    except (TypeError, ValueError):
        pass
```

LibreHardwareMonitor's `/data.json` serializes `RawValue` as a **formatted string
with units** — `"41.5 W"`, exactly like temperatures (`"53.0 °C"`). `float("41.5 W")`
raises `ValueError`, which is caught and the sensor is **silently dropped**.

Temperature does not hit this bug because `_lhm_celsius()` (`_lhm_celsius`, agent.py:287)
falls back to parsing the numbered prefix of the `Value` string. The power path has no
such fallback.

The macOS `macmon` power path is unaffected — `macmon pipe` emits plain numeric JSON
values.

## 3. Evidence

- Dry-run on the remote (`venv python agent.py --dry-run`) lists
  `Active collectors: ... power` but the exposition text contains
  `node_hwmon_temp_celsius` / `node_hwmon_sensor_label` lines and **no**
  `node_power_watts` line.
- Pushgateway group `{job="pc_agent", instance="Cracked-ITX"}` (`last_push_successful: true`,
  fresh pushes every ~15s) contains no `node_power_watts`.
- Direct LHM web-server read confirms Power-type nodes with `RawValue` strings.

## 4. Proposed Fix

Parse the power value the same way `_lhm_celsius` parses temperatures: prefer
`float(RawValue)`, else parse the numeric prefix of the `Value` string, and skip
non-positive results. Scope is `_walk_lhm()`'s Power branch plus a small shared helper.

Fix commit should land alongside a re-deploy note so the remote agent is re-pushed
after `git pull` + `bootstrap.py`.