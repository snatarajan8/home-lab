# Plan: Add Halo as a device on the Device Aggregate dashboard

**Status:** Proposed
**Created:** 2026-09-02
**Issue:** issues/halo-on-device-aggregate.md
**Decision:** decisions/halo-device-aggregate-integration.md (Option B)

## Objective

Make `node-exporter:9100` (Halo) selectable in the Device Aggregate `$device` dropdown,
populating every `node_*` panel for Halo, and add the process + container panels that
currently exist only on halo_aggregate — all filtered uniformly by `$device`.

## Changes

### 1. `services/monitoring/prometheus/prometheus.yml`
Add `relabel_configs` to the `process_exporter` and `podman_exporter` jobs so both export
with `instance="node-exporter:9100"` (matching the node_exporter job for Halo):

```yaml
relabel_configs:
  - source_labels: [__address__]
    target_label: instance
    replacement: 'node-exporter:9100'
```

Existing dashboards (halo_aggregate, container_overview) neither filter nor display those
instances, so they are unaffected.

### 2. `services/monitoring/dashboards/device_aggregate.json`
- Device variable (`$device`): change `definition` and `query` from
  `label_values(node_cpu_seconds_total{job="pc_agent"}, instance)` to
  `label_values(node_cpu_seconds_total{job=~"pc_agent|node_exporter"}, instance)`.
  Resulting options: `All`, `CK-Mac`, `Cracked-ITX`, `node-exporter:9100`. No per-panel
  changes needed for the existing node_* panels.
- Append a new row **"Process & Container Detail"** (after Power Detail, no reflow of
  existing panels) with these panels, copied from halo_aggregate with
  `instance=~"$device"` added, new unique panel ids (29+):
  - Top 10 Processes by CPU — `topk(10, rate(namedprocess_namegroup_cpu_seconds_total{instance=~"$device"}[5m]))`, table
  - Top 10 Processes by Memory — `topk(10, namedprocess_namegroup_memory_bytes{memtype="resident",instance=~"$device"})`, table
  - Top 10 Processes by Disk I/O — `topk(10, rate(namedprocess_namegroup_read_bytes_total{instance=~"$device"}[5m]) + rate(namedprocess_namegroup_write_bytes_total{instance=~"$device"}[5m]))`, table
  - Top 10 Containers by CPU — `topk(10, rate(podman_container_cpu_seconds_total{instance=~"$device"}[5m]) * on(id) group_left(name) podman_container_info)`
  - Top 10 Containers by Memory — `topk(10, podman_container_mem_usage_bytes{instance=~"$device"} * on(id) group_left(name) podman_container_info)`
  - Network Throughput by Container — `rate(podman_container_net_input_total{instance=~"$device"}[5m]) * on(id) group_left(name) podman_container_info` (+ output for tx)

## Verification

1. `docker compose restart prometheus`; wait one scrape cycle (15s).
2. Confirm via Prometheus API that `namedprocess_namegroup_*` and `podman_container_*`
   series now carry `instance="node-exporter:9100"`.
3. `python3 -m json.tool` both edited JSON/Prometheus configs to validate syntax.
4. Grafana file provisioner picks up dashboard edits automatically; confirm on
   `http://localhost:3000` that the Device dropdown lists `node-exporter:9100` and the
   new panels render for Halo (and process/container panels also work when that device is
   selected).

## Commit

Single atomic commit: prometheus.yml + device_aggregate.json + issue/decision/plan docs.
Push to `origin/main` only after user approval.