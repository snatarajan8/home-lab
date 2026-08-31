# Homelab Implementation To-Do List

This list tracks the progress of the homelab build and outlines the next steps for review and implementation.

## Completed

- [x] **Monitoring Stack Implementation**
    - [x] Provisioning configuration for Grafana.
    - [x] `System Overview` Dashboard (Stat panels for CPU, Memory, Disk, Temp).
    - [x] `System Trends` Dashboard (Timeseries for trends).
    - [x] Fixed dashboard provisioning directory structure.
- [x] **Design Phase (Homelab Recommendations)**
    - [x] Proxmox VE
    - [x] Docker Host (Ryzen Halo)
    - [x] Media/Storage Server
    - [x] Pi Zero (Edge Tier)
    - [x] Android Phone Repurposing
    - [x] Tailscale Implementation

## Pending Review

### 1. Monitoring Dashboards
- [x] **Process Monitoring Decision**: Resolved — see `decisions/dashboard-observability-depth.md`. The original `process-exporter` failure was a nonexistent image name (`stefanprodan/process-exporter`), not a registry block; the canonical `ncabatoff/process-exporter` image pulls fine. Its config file also had the wrong top-level YAML key (`process:` instead of `process_names:`), which silently tracked zero processes — fixed, now tracking 288 process groups including root-owned daemons.
- [x] **Verify Grafana Dashboards**: Confirmed via direct Prometheus queries (headless SSH session, no browser) — all 5 new detail dashboards return non-empty results for every panel query, including `Container Overview` (see below). Visual confirmation in an actual browser still recommended once you're at a non-headless client.
- [x] **Container-level visibility**: `cadvisor` doesn't work under rootless Podman (private cgroup namespace — root-caused in `issues/cadvisor-rootless-cgroupns-analysis.md`). Replaced with `podman-exporter` (`quay.io/navidys/prometheus-podman-exporter`), which talks to Podman's native API directly instead of reading cgroupfs, sidestepping the problem entirely. Verified working: real per-container CPU/memory/network data for all 6 stack containers.
- [x] **Verify Provisioning**: Confirmed — dropping new `.json` files into `services/monitoring/dashboards/` and restarting Grafana auto-registered all 5 new dashboards (no manual import needed). Path in this doc corrected — dashboards live here since the provisioning restructure, not under `provisioning/dashboards/`.

### Metric Agent (Cross-Platform)
- [x] **Root-caused missing PC temperatures** — agent ran in WSL2, which hides host
  thermal sensors. See `issues/pc-agent-temperature-missing-analysis.md`.
- [x] **Cross-platform native agent** — Windows/macOS/Linux, no WSL. Windows temps
  via LibreHardwareMonitor HTTP; macOS via opt-in `macmon`. Fixed the
  `node_cpu_seconds_total` rate-of-a-rate bug. See
  `docs/monitoring/cross-platform-metric-agent.md`.
- [x] **`bootstrap.py`** — one platform-agnostic script: detects OS, sets up the
  venv, installs macmon (macOS) / checks LibreHardwareMonitor (Windows), and
  registers the autostart service (launchd / systemd --user / Scheduled Task).
- [x] **Deploy on the Mac** — `bootstrap.py` run; launchd agent `com.homelab.metricagent` live.
- [ ] **Deploy on the PC (Cracked-ITX)** — install Python + LibreHardwareMonitor,
  then `python bootstrap.py` (replaces the WSL agent).

## Next Implementation Steps (Proposed)

### 2. Network & Access (Layer 3)
- [ ] **Tailscale Implementation**: Begin deploying Tailscale to the Ryzen host and main PC.
- [ ] **Nginx Proxy Manager**: Create a new service in `services/` to manage SSL and local DNS.
- [ ] **Pi-hole / AdGuard Home**: Create a new service for network-wide ad blocking.

### 3. Expansion
- [ ] **Pi Zero Deployment**: Design the edge-tier setup for MQTT/DNS.
- [ ] **Android Repurposing**: Implement specialized uses (cameras/dashboards).
