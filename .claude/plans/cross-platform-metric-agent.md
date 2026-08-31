# Implementation Plan: Cross-Platform Metric Agent

Decision doc: [`docs/monitoring/cross-platform-metric-agent.md`](../../docs/monitoring/cross-platform-metric-agent.md)
Issue: [`issues/pc-agent-temperature-missing-analysis.md`](../../issues/pc-agent-temperature-missing-analysis.md)

Supersedes `.claude/plans/pc-metric-collector.md` (WSL-only).

## Goals

1. **PC temperatures work** — Windows-native agent reads LibreHardwareMonitor.
2. **PC CPU / disk / network correct** — currently misreported (CPU is a
   rate-of-a-rate bug; disk/net describe the WSL `.vhdx` / virtual NIC).
3. **macOS agent** — same agent runs on this Mac and others, pushes to the same
   Pushgateway with the same `device` label.

No new server-side components. No new Python dependencies (HTTP via stdlib
`urllib`). Metric names/labels unchanged so existing dashboards keep working.

---

## Part A — Rework `services/monitoring/pc-agent/agent.py`

Single file, platform dispatch via `platform.system()` (`"Linux"`, `"Windows"`,
`"Darwin"`). Each collector that can't run on the current platform returns `[]`
and logs **once** at WARNING. Startup logs a one-line capability summary
(`active collectors: cpu,memory,disk,network,load; temp source: lhm-http`).

### A1. CPU — `node_cpu_seconds_total` back to a real counter *(bug fix)*

**Current:** emits per-second *rates* (0–~ncpu) under a `_total` name, plus a
synthetic `cpu="total"` series. Dashboards then apply `rate()` on top → garbage
(live check: "CPU Usage" panel reads 92.9% on a 99.9%-idle box).

**Fix:** delete the stateful `_prev_cpu_times` rate machinery. Emit cumulative
seconds straight from `psutil.cpu_times(percpu=True)`, per-core only, matching
node_exporter exactly:

```
node_cpu_seconds_total{device="<d>",cpu="0",mode="user"} <cumulative seconds>
```

- Drop the `cpu="total"` series entirely (node_exporter has none; it was the
  source of the earlier "negative CPU%" that the rate-hack was meant to fix).
- `modes` list + `hasattr` guard already handles per-platform fields
  (Windows: user/system/idle/interrupt/dpc; macOS: user/nice/system/idle).
- Dashboards already do `rate(node_cpu_seconds_total{mode="idle"}[5m])` → now
  correct on every platform, no dashboard change needed for CPU.

### A2. Memory — unchanged

`psutil.virtual_memory()` / `swap_memory()`; `buffers`/`cached` stay
`getattr(..., 0)` guarded (Linux-only). Works as-is on all three platforms.

### A3. Disk — real filesystems + `fstype` label

- Default `disk_paths` becomes **auto-detect**: iterate
  `psutil.disk_partitions(all=False)`, skip pseudo/virtual fstypes
  (`tmpfs`, `devtmpfs`, `overlay`, `squashfs`, `proc`, `sysfs`, `autofs`,
  `devfs`, `none`), and skip macOS system-snapshot/`nobrowse` mounts. Config
  `disk_paths:` (explicit list) still overrides.
- Emit with an `fstype` label and the real mountpoint:

```
node_filesystem_size_bytes{device="<d>",mountpoint="C:\\",fstype="NTFS"}  <bytes>
node_filesystem_free_bytes{device="<d>",mountpoint="C:\\",fstype="NTFS"}  <bytes>
node_filesystem_avail_bytes{device="<d>",mountpoint="C:\\",fstype="NTFS"} <bytes>
```

- `node_disk_*` I/O counters: keep `psutil.disk_io_counters()` (cumulative
  counter — already correct; works on Windows/macOS).

### A4. Network — unchanged

`psutil.net_io_counters(pernic=True)` cumulative counters — already correct
cross-platform. Keep aggregate + per-interface series.

### A5. Temperature — platform-specific sources

New structure:

```python
def collect_temperature(cfg, device):
    system = platform.system()
    if system == "Linux":   return _temp_linux(device)          # psutil.sensors_temperatures()
    if system == "Windows": return _temp_windows(cfg, device)   # LHM
    if system == "Darwin":  return _temp_macos(cfg, device)     # macmon (opt-in)
    return []
```

- **`_temp_linux`** — existing `psutil.sensors_temperatures()` logic, kept for
  bare-metal Linux devices. (The WSL PowerShell fallback is **removed** — WSL is
  no longer a supported target.)

- **`_temp_windows`** — HTTP `GET` `cfg["lhm_url"]`
  (default `http://localhost:8085/data.json`) via `urllib`, 5 s timeout.
  Recursively walk the LHM tree; for every node with `Type == "Temperature"`,
  parse `Value` (`"45.3 °C"` → `45.3`), use the nearest ancestor hardware node's
  `Text` as `chip`, the sensor node's `Text` as `sensor`. Emit
  `node_hwmon_temp_celsius{device,chip,sensor}` + the matching
  `node_hwmon_sensor_label{...,label=sensor} 1`.
  - Unreachable / connection refused → log **once** at WARNING
    (`"LibreHardwareMonitor not reachable at <url> — no Windows temps"`),
    return `[]`.
  - Optional degraded fallback: `windows_temp_source: acpi` in config re-enables
    the old `MSAcpi_ThermalZoneTemperature` PowerShell query. Default `lhm`.

- **`_temp_macos`** — only if `cfg["mac_temp_source"] == "macmon"` **and**
  `shutil.which("macmon")`. Run `macmon pipe -s 1 -i 200` (one sample), read the
  last JSON line, extract `temp.cpu_temp_avg` / `temp.gpu_temp_avg`, emit:

```
node_hwmon_temp_celsius{device="<d>",chip="soc",sensor="cpu"} <c>
node_hwmon_temp_celsius{device="<d>",chip="soc",sensor="gpu"} <c>
```

  Default `mac_temp_source: none` → return `[]`, log once at INFO
  (`"macOS temps disabled (set mac_temp_source: macmon and install macmon)"`).

- Replace the blanket `except (..., Exception)` with specific exceptions
  (`urllib.error.URLError`, `OSError`, `subprocess.SubprocessError`,
  `json.JSONDecodeError`, `ValueError`).

### A6. Load — `psutil.getloadavg()` (cross-platform)

Swap `os.getloadavg()` → `psutil.getloadavg()` (psutil emulates on Windows;
native on Linux/macOS). Keep `node_load1/5/15`. First ~5 s on Windows reports
`0.0` — acceptable.

### A7. Uptime / job name

- `collect_uptime` unchanged (`psutil.boot_time()` works everywhere).
- Push job stays **`pc_agent`** (renaming would break the dashboard template
  variable for no real gain; the `device` label already distinguishes Mac vs PC).
  Add `job:` to `config.yaml` defaulting to `pc_agent` for future flexibility.

---

## Part B — Config, launchers, packaging

### B1. `services/monitoring/pc-agent/config.yaml`

```yaml
pushgateway_url: "http://amd-halo:9091"
push_interval: 15
job: "pc_agent"

metrics:
  cpu: true
  memory: true
  disk: true
  network: true
  temperature: true
  load: true
  # disk_paths: []        # empty/omitted = auto-detect real filesystems

# Windows only: "lhm" (LibreHardwareMonitor HTTP) | "acpi" (degraded) | "none"
windows_temp_source: "lhm"
lhm_url: "http://localhost:8085/data.json"

# macOS only: "macmon" | "none"
mac_temp_source: "none"
```

`load_config()` gains defaults for `job`, `windows_temp_source`, `lhm_url`,
`mac_temp_source`.

### B2. New `push-metrics.ps1` (Windows launcher)

PowerShell equivalent of `push-metrics`: find `python`/`py`, create `.venv`,
`pip install -r requirements.txt` if psutil missing, `python agent.py -c config.yaml`.

### B3. New `com.homelab.metricagent.plist` (macOS launchd)

`launchd` user-agent plist: runs `push-metrics`, `KeepAlive=true`,
`RunAtLoad=true`, logs to `~/Library/Logs/homelab-metric-agent.log`.
README documents `launchctl load ~/Library/LaunchAgents/...`.

### B4. `requirements.txt` — unchanged (`psutil`, `pyyaml`).

### B5. `README.md` — full rewrite

Three platform sections:
- **Linux** — `./push-metrics`, systemd unit (existing content).
- **Windows** — install Python; install **LibreHardwareMonitor**, enable
  *Options → Remote Web Server → Run* (port 8085) and *Run on Windows startup* +
  run LHM as admin (or a Task Scheduler task at logon, highest privileges);
  `push-metrics.ps1`; Task Scheduler snippet for the agent.
- **macOS** — `./push-metrics`; optional `brew install macmon` +
  `mac_temp_source: macmon`; `launchd` plist install.
- Update "Metrics Collected" table (note temp availability per platform).
- Remove all WSL instructions.

---

## Part C — Dashboard fixes (`services/monitoring/dashboards/`)

### C1. `device_aggregate.json`

- **Panel 4 "Disk Usage (/)"** → **"Disk Usage"**, aggregate across all reported
  filesystems for the device:
  ```
  100 - (sum by (instance)(node_filesystem_avail_bytes{instance=~"$device"})
       / sum by (instance)(node_filesystem_size_bytes{instance=~"$device"}) * 100)
  ```
  (drops the `mountpoint="/"` filter that never matches Windows `C:\`).
- **Panel 20 "Disk Usage by Mountpoint"** — keep, but change `fstype!~"tmpfs"`
  to an explicit real-fs allow (`fstype=~"NTFS|apfs|ext4|xfs|btrfs|vfat|exfat|zfs"`)
  or just `mountpoint!=""` — now that `fstype` is emitted.
- **Panel 5 "Max Temperature"** — leave query (`max by (instance)(...)`); it works
  once temps flow. No label-join added (keep it a simple number).
- CPU panels (2, 7, 12): **no change** — they become correct once A1 lands.

### C2. `aggregate.json`

- **"Disk Usage (/)"** panel — same aggregate rewrite as C1 panel 4, on both
  the `instance` (Halo) and `device` (remote) branches of the `or`.
- Other panels unchanged (CPU/net/disk-IO already `rate()` counters; temp
  fallback `max by (device)` works once temps flow).

### C3. Other dashboards — no change

`halo_aggregate.json` (filtered `job="node_exporter"`), `system_overview`,
`system_trends`, `*_detail.json` are Halo-scoped.

---

## Part D — Doc housekeeping

- `docs/monitoring/pc-metric-collector-agent.md` — add a top banner: *"Platform
  decision superseded by `cross-platform-metric-agent.md` (2026-08-31). WSL-only
  is retired."*
- `.claude/plans/pc-metric-collector.md` — add superseded banner.
- `MEMORY.md` + `services/monitoring/` memory — the index line points at
  `decisions/metrics-aggregation-strategy.md`, which does not exist (the file is
  `docs/monitoring/metrics-aggregation-strategy.md`). Fix the path; add a pointer
  to the new decision doc.
- `TODO.md` — tick the monitoring/agent items as appropriate; add a line for
  "cross-platform metric agent".

---

## Part E — Verification

**Static / local:**
1. `python3 -m py_compile agent.py`.
2. Run `agent.py` on this Mac (`push_interval` short, dry-run print mode via a
   `--dry-run` flag added to dump exposition text to stdout instead of pushing).
   Confirm: valid Prometheus text, `device=` on every line, per-core
   `node_cpu_seconds_total` are large monotonic counters, `node_filesystem_*`
   show the real APFS volumes, `node_load1` non-zero.
3. With `mac_temp_source: none` → no temp lines, one INFO log. If `macmon`
   installed, flip to `macmon` → two `node_hwmon_temp_celsius` lines.

**Against the live stack (Mac push):**
4. Let the Mac agent push for ~2 min. On `http://amd-halo:9090`:
   - `node_cpu_seconds_total{device="<mac-hostname>"}` present, counter-shaped;
     `rate(...[2m])` in `[0,1]` per core.
   - `100 - avg by(instance)(rate(node_cpu_seconds_total{device="<mac>",mode="idle"}[5m]))*100`
     ≈ real CPU load (sanity-check against Activity Monitor).
   - `node_filesystem_*`, `node_network_*`, `node_load1` present and sane.
5. `Device Aggregate` dashboard: `$device` selector lists the Mac; CPU / Memory /
   Disk / Load / Network panels populate; Temperature panels empty (expected
   without macmon) or populated (with).

**Windows (user-side, documented — I can't run it here):**
6. README checklist: LHM web server returns JSON at `:8085/data.json`; run the
   agent; `node_hwmon_temp_celsius{device="Cracked-ITX"}` appears with real
   `k10temp`/GPU/NVMe sensors; CPU panel now reads a sane low % at idle;
   `node_filesystem_*` shows real `C:\` size, not 1.08 TB.

**Regression:**
7. Confirm Halo's own `node_exporter` series and `halo_aggregate` dashboard are
   untouched (no agent or prometheus.yml change affects them).

---

## Part F — Commit & PR

Branch `feat/cross-platform-metric-agent` (already open as PR #1). Atomic commits:

1. `fix(pc-agent): emit node_cpu_seconds_total as a real counter` (A1)
2. `feat(pc-agent): cross-platform collectors (Windows/macOS/Linux)` (A2–A7, B1)
3. `feat(pc-agent): Windows LHM + macOS macmon temperature sources` (A5 detail)
4. `feat(pc-agent): Windows + macOS launchers, rewrite README` (B2–B5)
5. `fix(monitoring): device dashboard disk panels; doc housekeeping` (C, D)

Then update PR #1 body, mark ready for review.

## Out of scope

- Renaming the `pc-agent/` directory or the `pc_agent` push job.
- GPU utilisation, Windows services/update status, per-process metrics on remote
  devices.
- Alerting on stale pushgateway series.
- Intel-Mac temperature path (note in README: `powermetrics`/`osx-cpu-temp`).
