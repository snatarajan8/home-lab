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
- [x] **Verify Grafana Dashboards**: Confirmed via direct Prometheus queries (headless SSH session, no browser) — `System Overview`/`System Trends` corrected CPU/temperature queries return data; `CPU Detail`, `Memory & Process Detail`, `Temperature Detail`, `Disk & I/O Detail` all return non-empty results for every panel query.
    - [ ] **`Container Overview` is provisioned but non-functional** — `cadvisor` can't see per-container cgroup stats under rootless Podman (private cgroup namespace, `cgroup: host` doesn't propagate through Podman's Docker-compat layer). Root-caused in `issues/cadvisor-rootless-cgroupns-analysis.md`; possible fix is a native Podman-stats-API exporter instead of cadvisor. Open — visual confirmation in an actual browser still recommended once you're at a non-headless client.
- [x] **Verify Provisioning**: Confirmed — dropping new `.json` files into `services/monitoring/dashboards/` and restarting Grafana auto-registered all 5 new dashboards (no manual import needed). Path in this doc corrected — dashboards live here since the provisioning restructure, not under `provisioning/dashboards/`.

## Next Implementation Steps (Proposed)

### 2. Network & Access (Layer 3)
- [ ] **Tailscale Implementation**: Begin deploying Tailscale to the Ryzen host and main PC.
- [ ] **Nginx Proxy Manager**: Create a new service in `services/` to manage SSL and local DNS.
- [ ] **Pi-hole / AdGuard Home**: Create a new service for network-wide ad blocking.

### 3. Expansion
- [ ] **Pi Zero Deployment**: Design the edge-tier setup for MQTT/DNS.
- [ ] **Android Repurposing**: Implement specialized uses (cameras/dashboards).
