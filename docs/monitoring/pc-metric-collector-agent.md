# PC Metric Collector Agent

## Context

The monitoring stack on the Ryzen Halo currently collects metrics only from local exporters (node-exporter, glances, process-exporter, podman-exporter) via Prometheus's pull model. We need a way for remote PCs (and this WSL session) to push the same performance metrics to the Halo, where they can be dashboarded alongside the Halo's own metrics.

The `metrics-aggregation-strategy.md` decision already selected **Prometheus Pushgateway** as the central aggregation mechanism. This doc determines the **client-side agent** that collects metrics on each PC and pushes them to the Pushgateway.

### Requirements
- Collect CPU, memory, disk, network, and temperature metrics
- Push metrics to the Halo's Pushgateway via HTTP POST
- Tag all metrics with a `device` label for per-device dashboard filtering
- Generic enough to onboard new PCs with minimal configuration
- Must work on Windows, Linux, and WSL (this session is from WSL)

## Comparison of Approaches

| Approach | How it Works | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **Python + psutil** | Python script using `psutil` library to collect system metrics, pushes via `requests` or `urllib` to Pushgateway | • True cross-platform (Windows, Linux, WSL, macOS) — same code, same behavior everywhere.<br>`psutil` is mature, well-documented, exposes CPU/memory/disk/network/temperature natively.<br>Easy to configure (YAML config for device name, push interval, Pushgateway URL).<br>Simple to extend — adding a new metric is one `psutil` call.<br>Can run as a background service, cron job, or manual execution.<br>Python is pre-installed on most Linux distros and WSL; on Windows, widely available via python.org or winget. | • Requires Python 3.8+ on target (~10MB with psutil).<br>Slightly higher resource footprint than a shell script (~5-10MB RAM).<br>Two dependencies to manage (python + psutil). |
| **Shell script + curl** | Bash/POSIX script parsing `/proc` or system commands, POSTs text format via `curl` | • Zero dependencies on Linux/WSL (curl is ubiquitous).<br>Very lightweight (~1MB RAM).<br>Easy to read and modify for Linux-savvy users. | • **No Windows support** — would need a separate PowerShell version or WSL wrapper.<br>Metrics collection is fragile — parsing `free`, `vmstat`, `/proc/stat` output varies across distros.<br>No temperature access without `lm-sensors` and parsing `sensors` output.<br>Harder to add new metrics (manual parsing per platform).<br>No proper error handling or retry logic. |
| **Go binary** | Statically compiled binary using `gopsutil` or reading `/proc` directly | • Single zero-dependency binary — no runtime needed.<br>Very lightweight (~5-10MB binary, ~5MB RAM).<br>Fast execution.<br>Cross-compilation possible (GOOS/GOARCH). | • Requires Go toolchain to build (or pre-compiled releases per platform).<br>Harder to modify — any change requires recompilation.<br>More complex to develop and debug.<br>Overkill for a simple HTTP POST script.<br>Binary size grows if bundling temperature/platform-specific code. |

## Evaluation Matrix

| Criterion | Python + psutil | Shell + curl | Go binary |
| :--- | :---: | :---: | :---: |
| Cross-platform (Win/Linux/WSL) | Excellent | Poor | Good |
| Ease of onboarding | High (pip install) | Medium (copy script) | Low (download binary) |
| Metric accuracy | Excellent (psutil native) | Low (parsed output) | Good (direct /proc) |
| Temperature support | Excellent (psutil.sensors) | Poor (needs lm-sensors) | Good (platform code) |
| Ease of modification | High (edit Python) | High (edit script) | Low (recompile) |
| Resource footprint | Low (~10MB) | Minimal (~1MB) | Low (~5MB) |
| Error handling/retry | Excellent (try/except) | Poor (manual traps) | Good |
| Configuration simplicity | Excellent (YAML) | Medium (env vars) | Good (YAML/flags) |

## Decision: WSL Standardization

### Context

All target PCs are Windows machines with WSL2 available. The question is whether to:
- **Option A:** Standardize on WSL for all metric collection (require WSL on every PC)
- **Option B:** Support both Windows native and WSL/Linux (cross-platform agent)

### Evaluation

| Criterion | WSL Standardization | Cross-Platform |
| :--- | :---: | :---: |
| Temperature sensors | Full (/sys/class/thermal) | None on Windows |
| Load averages | Native (getloadavg) | None on Windows |
| Metric consistency | Identical across all PCs | Varies by platform |
| Agent code complexity | Low (single platform) | Medium (platform detection) |
| Service management | systemd (standard) | systemd + Windows Service |
| Onboarding friction | Low (WSL2 is built into Win10/11) | None (runs anywhere) |
| Windows-native metrics | Not available | Available (GPU, services) |
| Testing surface | 1 platform | 2+ platforms |

### Recommendation: WSL Standardization

**Rationale:**
1. **Metric completeness:** Temperature and load averages are only available on Linux/WSL. A Windows-native agent would have reduced functionality, creating inconsistent dashboards across devices.
2. **Consistency:** All PCs produce identical metrics with identical labels. Dashboards work the same everywhere.
3. **Simplicity:** Single codebase, no platform detection, no conditional logic. The agent is a simple Python script that runs the same way on every machine.
4. **Low friction:** WSL2 is built into Windows 10 1903+ and Windows 11. Installation is a single command (`wsl --install`). For a homelab audience, this is a reasonable prerequisite.
5. **Ecosystem alignment:** The entire monitoring stack (Prometheus, Grafana, node-exporter) is Linux-native. WSL gives us a native Linux environment on Windows hardware.

**Trade-off acknowledged:** Windows-native metrics (GPU usage via DXGI, Windows Update status, Windows services) will not be available. This is acceptable — GPU temperature is available via WSL's `/sys/class/thermal`, and the primary goal is CPU/memory/disk/network visibility, not Windows-specific health checks.

## Decision: Python + psutil

### Rationale

The primary constraint is **cross-platform compatibility**. The user's environment includes WSL (Linux) on a Windows PC, and future PCs may run either OS natively. Python + psutil is the only approach that works identically across all three platforms without maintaining separate codebases.

The `psutil` library provides first-class access to exactly the metrics we need:
- `psutil.cpu_percent(interval, percpu)` — per-core CPU usage
- `psutil.virtual_memory()` — total/available/used/buffers/cached
- `psutil.disk_usage(path)` — per-mountpoint disk usage
- `psutil.disk_io_counters()` — disk read/write bytes
- `psutil.net_io_counters()` — network bytes sent/received
- `psutil.sensors_temperatures()` — per-sensor temperatures (Linux/WSL; gracefully degraded on Windows)
- `psutil.getloadinfo()` / `os.getloadavg()` — load averages

The Halo's existing dashboards query `node_cpu_seconds_total`, `node_memory_*`, `node_filesystem_*`, `node_disk_*`, `node_network_*`, and `node_hwmon_temp_celsius`. The Pushgateway agent will push metrics in Prometheus exposition format using the same metric names (or compatible equivalents), prefixed with a `device` label, so the same PromQL patterns work across both local and remote metrics.

### Configuration

The agent will use a simple YAML config file:

```yaml
device_name: "shyam-pc"          # Unique identifier for this device
pushgateway_url: "http://<halo-ip>:9091"  # Pushgateway endpoint
push_interval: 15                # Seconds between pushes
metrics:
  cpu: true
  memory: true
  disk: true
  network: true
  temperature: true
  disk_paths: ["/"]              # Mountpoints to report (Linux) or ["C:\\"] (Windows)
```

### Onboarding a New PC

1. Ensure WSL2 is installed on the Windows PC (`wsl --install`)
2. Clone/copy the agent directory into the WSL filesystem
3. Install Python 3.8+ if not present (`sudo apt install python3 python3-pip`)
4. `pip install -r requirements.txt` (psutil, pyyaml, requests)
5. Edit `config.yaml` with a unique `device_name`
6. Run: `python3 agent.py` (or set up as a systemd service)

### Metric Naming Convention

The agent will push metrics using Prometheus Pushgateway's text format, with a `device` label on every metric:

```
# HELP node_cpu_seconds_total Seconds the CPUs spent in each mode.
# TYPE node_cpu_seconds_total counter
node_cpu_seconds_total{device="shyam-pc",cpu="0",mode="idle"} 12345.67
node_cpu_seconds_total{device="shyam-pc",cpu="0",mode="user"} 678.90
```

This ensures:
- Halo's own metrics have `instance="node-exporter:9100"` (no `device` label)
- PC metrics have `device="shyam-pc"` (no `instance` label from node-exporter)
- Dashboards can use `or` filters or template variables to show both

### Dashboard Integration

Existing dashboards will need a **template variable** (`$device`) that lists all devices. New PC-specific dashboards will be created alongside the existing Halo dashboards, with the device variable pre-configured. The Pushgateway itself will also be added as a scrape target in `prometheus.yml`.

## Final Outcome

Selected: **WSL-only + Python + psutil** agent, pushed via Prometheus Pushgateway, with YAML configuration and a `device` label convention for multi-device dashboard support.

### Decisions Made

1. **Target platform: WSL-only** — All metric collection runs on WSL on Windows PCs. This ensures full metric availability (temperature, load averages) and consistent behavior across all devices. Windows-native support is explicitly out of scope.
2. **Agent language: Python + psutil** — Single codebase, cross-platform within Linux/WSL, mature library for system metrics.
3. **Transport: Prometheus Pushgateway** — Devices push metrics to the Halo; Prometheus scrapes the Pushgateway.
4. **Labeling: `device` label** — Every pushed metric carries a `device` label for per-device dashboard filtering.

### What This Enables

- Any WSL instance can onboard as a monitoring target in ~5 minutes
- Dashboards auto-discover new devices via `label_values(node_cpu_seconds_total, device)`
- Same PromQL patterns work for both Halo (local node-exporter) and remote PCs (pushed via Pushgateway)
