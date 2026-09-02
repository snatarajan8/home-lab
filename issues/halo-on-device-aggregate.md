# Issue: Add Halo as a device on the Device Aggregate dashboard

**Status:** Proposed
**Created:** 2026-09-02
**Area:** services/monitoring/dashboards/device_aggregate.json

## Problem

On the "Device Aggregate" dashboard the Device dropdown (`$device`) is populated by:

```
label_values(node_cpu_seconds_total{job="pc_agent"}, instance)
```

which lists only agents pushing to the Pushgateway (`CK-Mac`, `Cracked-ITX`). Halo
publishes via the `node_exporter` job (instance `node-exporter:9100`) and never appears
in the dropdown. Only Halo's power panels show today, because those three panels hardcode
`node_hwmon_power_watt{job="node_exporter"}` targets. Every other panel uses
`instance=~"$device"` and stays empty for Halo.

## Requested outcome

1. Halo selectable as a device on Device Aggregate so all its node metrics appear
   (overview stats, CPU/mem/disk/network/io trends, per-core CPU, load, memory breakdown,
   swap, disk by mountpoint, temps, power).
2. Bring over everything that exists on halo_aggregate but not on device_aggregate,
   so nothing Halo can show is missing:
   - Top 10 Processes by CPU
   - Top 10 Processes by Memory
   - Top 10 Processes by Disk I/O
   - Container Overview row (Top 10 Containers by CPU, Top 10 Containers by Memory,
     Network Throughput by Container)

## Constraints / observations

- All `node_*` panels already use `instance=~"$device"`, so adding the Halo instance to
  the variable makes them work with zero per-panel changes.
- Process metrics (`process_exporter` job) and container metrics (`podman_exporter` job)
  carry instance labels `process-exporter:9256` and `podman-exporter:9882` respectively
  — these do not match any `$device` value, so process/container panels cannot reuse the
  `$device` filter unless instances are aligned.
- Grafana provisions dashboards from `services/monitoring/dashboards/` (folder-mounted
  read-only); file edits are picked up by the provisioner, no manual import required.