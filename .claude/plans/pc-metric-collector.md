# Implementation Plan: PC Metric Collector Agent

## Overview

Add a Prometheus Pushgateway to the Halo's monitoring stack. Create a Python agent (psutil) that runs on WSL on any Windows PC, collects system metrics, and pushes them to the Pushgateway. Create Grafana dashboards with device-level filtering.

**Key decision:** WSL-only. All metric collection runs on WSL (not Windows native). See `docs/monitoring/pc-metric-collector-agent.md` for rationale.

---

## Step 1: Add Pushgateway to Halo Monitoring Stack ✅

**File:** `services/monitoring/docker-compose.yml`

Added `pushgateway` service with `prom/pushgateway:latest`, port 9091, cap_drop ALL, 0.3 CPU / 128M limits.

---

## Step 2: Add Pushgateway as Prometheus Scrape Target ✅

**File:** `services/monitoring/prometheus/prometheus.yml`

Added scrape job with `honor_labels: true` to preserve the `device` label from pushed metrics.

---

## Step 3: Create Python Agent ✅

**Directory:** `services/monitoring/pc-agent/`

```
pc-agent/
├── agent.py           # Main agent (psutil collection + Pushgateway push)
├── config.yaml        # Device configuration (device_name inferred from hostname)
├── push-metrics       # Launcher script (auto-installs deps)
├── requirements.txt   # psutil, pyyaml
└── README.md          # Onboarding instructions
```

- Device name is **inferred from WSL hostname** — no manual config needed
- Config only requires `pushgateway_url`
- `push-metrics` script auto-installs dependencies and launches the agent

---

## Step 4: Create Grafana Dashboards ✅

**Directory:** `services/monitoring/dashboards/`

- `remote_devices_overview.json` — Stat panels: CPU, Memory, Disk, Temp, Load, Network Rx (with `$device` variable)
- `remote_devices_trends.json` — Timeseries panels: CPU by device, Temp by device, Memory by device, Network by device

Both use `label_values(node_cpu_seconds_total, device)` for auto-discovery.

---

## Step 5: Reorganize Monitoring Docs ✅

Moved all monitoring docs into `docs/monitoring/`:
- `monitoring-strategy.md`
- `metrics-aggregation-strategy.md`
- `dashboard-observability-depth.md`
- `grafana-provisioning-strategy.md`
- `new-dashboards-metrics.md`
- `pc-metric-collector-agent.md`
- `cadvisor-rootless-cgroupns-analysis.md`
- `monitoring_dashboard_failure.md`

---

## Step 6: Run Scripts ✅

- `run-metrics-server.sh` — Starts the full Halo monitoring stack (docker compose)
- `pc-agent/push-metrics` — Starts the metric push agent on auxiliary PCs

Old `run.sh` removed.

---

## Verification

1. `curl http://<halo-ip>:9091/-/healthy` → 200
2. Run `./push-metrics` on WSL → metrics at `http://<halo-ip>:9091/metrics`
3. Prometheus targets page shows Pushgateway as UP
4. `node_cpu_seconds_total{device="<hostname>"}` returns data
5. Remote Devices dashboards show PC metrics
6. Device selector auto-populates with new device name
