# Decision: How to wire Halo's process/container metrics into Device Aggregate

**Status:** Proposed
**Created:** 2026-09-02
**Issue:** issues/halo-on-device-aggregate.md

## Context

Adding Halo to the Device Aggregate `$device` variable naturally makes every existing
`node_*` panel work for Halo (they already filter on `instance=~"$device"`). The open
question is how the process tables and container row — copied from halo_aggregate —
interact with the device selector.

Metric → instance mapping today:

| Job               | Instance                | Device |
|-------------------|-------------------------|--------|
| `node_exporter`   | `node-exporter:9100`    | Halo   |
| `process_exporter`| `process-exporter:9256` | Halo*  |
| `podman_exporter` | `podman-exporter:9882`  | Halo*  |
| `pc_agent`        | `CK-Mac`, `Cracked-ITX` | Mac, Cracked-ITX |

\* exporters run on the Halo host.

Because process/podman instances differ from `node-exporter:9100`, a plain
`instance=~"$device"` filter would leave the copied process/container panels empty when
`node-exporter:9100` (Halo) is selected.

## Option A — Copy panels unfiltered (no infra change)

Copy the three process tables and the container row exactly as they exist in
halo_aggregate (no instance filter). They always show Halo's data regardless of the
device selection, since those exporters only run on Halo.

- Pros: zero infrastructure change; faithful copy of halo_aggregate behavior; no
  Prometheus reload.
- Cons: panels ignore the device selector (they will show Halo data even when a
  different device is selected) — slightly inconsistent with the per-device concept;
  if a second node ever runs process-exporter, it would bleed into the panels.

## Option B — Align instance labels + filter by `$device` (recommended)

Add a relabel to the `process_exporter` and `podman_exporter` scrape jobs in
`prometheus.yml` so both export with `instance="node-exporter:9100"`. Then the copied
process/container panels can use `{instance=~"$device"}` like every other panel.

- Pros: single coherent "Halo = node-exporter:9100" identity across all metric families;
  the device selector works uniformly across every panel; future-proof (a second node's
  exporters get their own instance and slot in automatically).
- Cons: touches `prometheus.yml` and needs a Prometheus reload (`docker compose restart
  prometheus`); series instance labels change for the process/podman jobs (nothing in the
  existing dashboards depends on those instance values — halo_aggregate and the standalone
  container_overview dashboard neither filter nor display them).
- Fallback safety: `git` tracked, reload is quick, and existing dashboards are unaffected.

## Recommendation

Option B. It keeps the dashboard internally consistent and matches the user's mental
model ("a device shows everything that device publishes"), at the cost of one small
scrape-config change and a Prometheus reload.

## Outcome

**Selected: Option B** (2026-09-02, user). Relabel `process_exporter`/`podman_exporter`
to `instance="node-exporter:9100"` and filter the copied process/container panels with
`instance=~"$device"`.