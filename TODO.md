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
- [ ] **Verify Grafana Dashboards**: Access `http://localhost:3000` and check:
    - `System Overview`: Ensure metrics for CPU, Memory, Disk, and Temperature are visible and correct.
    - `System Trends`: Ensure time-series graphs are populating correctly.
- [ ] **Verify Provisioning**: Confirm that new `.json` files added to `services/monitoring/provisioning/dashboards/` appear automatically.
- [ ] **Process Monitoring Decision**: I attempted to add `process-exporter` but encountered registry access errors.
    - *Option A*: Use `glances_processcount` as a light-weight alternative.
    - *Option B*: Build `process-exporter` from source in a custom container.
    - *Option C*: Try a different image if you have a preferred one.

## Next Implementation Steps (Proposed)

### 2. Network & Access (Layer 3)
- [ ] **Tailscale Implementation**: Begin deploying Tailscale to the Ryzen host and main PC.
- [ ] **Nginx Proxy Manager**: Create a new service in `services/` to manage SSL and local DNS.
- [ ] **Pi-hole / AdGuard Home**: Create a new service for network-wide ad blocking.

### 3. Expansion
- [ ] **Pi Zero Deployment**: Design the edge-tier setup for MQTT/DNS.
- [ ] **Android Repurposing**: Implement specialized uses (cameras/dashboards).
