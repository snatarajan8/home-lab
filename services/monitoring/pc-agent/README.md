# Homelab Metric Agent

Lightweight cross-platform agent that collects system metrics and pushes them to
the Prometheus Pushgateway on the Halo server. Runs **natively** on Windows,
macOS, and Linux — no WSL.

Metrics are pushed in Prometheus exposition format using `node_*` names with a
`device="<hostname>"` label, so they land next to the Halo's own `node_exporter`
series and the `Device Aggregate` / `Aggregate` Grafana dashboards pick them up
automatically.

> **Why native, not WSL?** WSL2 does not expose the host's thermal sensors
> (`/sys/class/thermal` is empty) and misreports disk/network as the WSL VM's
> virtual devices. See
> [`issues/pc-agent-temperature-missing-analysis.md`](../../../issues/pc-agent-temperature-missing-analysis.md)
> and [`docs/monitoring/cross-platform-metric-agent.md`](../../../docs/monitoring/cross-platform-metric-agent.md).

## Config (`config.yaml`)

```yaml
pushgateway_url: "http://amd-halo:9091"   # required
push_interval: 15
job: "pc_agent"
# device_name: "my-box"                   # optional; defaults to the hostname
metrics:
  cpu: true
  memory: true
  disk: true
  network: true
  temperature: true
  load: true
  # disk_paths: ["/"]                      # optional; omit to auto-detect
windows_temp_source: "lhm"                 # lhm | acpi | none
lhm_url: "http://localhost:8085/data.json"
mac_temp_source: "none"                    # macmon | none
```

Set `device_name` explicitly if your hostname is ugly (e.g. an MDM-assigned
serial) — it becomes the dashboard's device label.

---

## Linux

```bash
pip install -r requirements.txt   # or let ./push-metrics make a venv
vim config.yaml
./push-metrics
```

Temperature comes from `psutil.sensors_temperatures()` (hwmon: `coretemp`,
`k10temp`, `nvme`, `amdgpu`, …) — nothing extra to install.

**systemd (auto-start):**

```ini
# /etc/systemd/system/homelab-metric-agent.service
[Unit]
Description=Homelab Metric Agent
After=network-online.target

[Service]
ExecStart=/path/to/pc-agent/push-metrics
Restart=always
User=%i

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now homelab-metric-agent
```

---

## Windows (native)

### 1. Install Python 3

`winget install Python.Python.3.12` (or from python.org). Confirm `py -3 --version`.

### 2. Install LibreHardwareMonitor (for temperatures)

`psutil` cannot read temperatures on Windows, and the ACPI thermal zone is
unsupported on most desktop boards. LibreHardwareMonitor (free, open-source) reads
the CPU/GPU/SSD/board sensors directly.

1. Download from <https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases>
   and extract somewhere permanent (e.g. `C:\Tools\LibreHardwareMonitor`).
2. Launch it, then **Options →**
   - ✔ **Run On Windows Startup**
   - ✔ **Start Minimized** / **Minimize To Tray**
   - ✔ **Run As Administrator on Startup** (needed for the full sensor set)
   - **Remote Web Server → Port = 8085**, then ✔ **Run**
3. Verify: browse to <http://localhost:8085/data.json> — you should get a JSON tree.

If you'd rather not run LHM, set `windows_temp_source: "acpi"` (degraded, often
empty) or `"none"` in `config.yaml`.

### 3. Run the agent

```powershell
.\push-metrics.ps1
```

### 4. Auto-start at logon (Task Scheduler)

```powershell
# Run PowerShell as Administrator, from this directory
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -File `"$PWD\push-metrics.ps1`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName "HomelabMetricAgent" -Action $action `
    -Trigger $trigger -Settings $settings -RunLevel Highest `
    -Description "Push system metrics to the Halo Pushgateway"
```

---

## macOS

```bash
./push-metrics
```

Temperature: Apple Silicon exposes no sensors to `psutil`. To get CPU/GPU temps,
install [`macmon`](https://github.com/vladkens/macmon) (sudoless) and enable it:

```bash
brew install macmon
# config.yaml:
mac_temp_source: "macmon"
```

Intel Macs: temps would need `powermetrics` (sudo) or `osx-cpu-temp` — not wired
up; leave `mac_temp_source: "none"`.

**launchd (auto-start):** edit the path in `com.homelab.metricagent.plist`, then

```bash
cp com.homelab.metricagent.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.homelab.metricagent.plist
```

---

## Onboarding a new device

1. Copy this `pc-agent/` directory onto the device.
2. Install Python 3 (and LibreHardwareMonitor on Windows / `macmon` on Apple Silicon).
3. Edit `config.yaml` — at minimum `pushgateway_url`; set `device_name` if needed.
4. `./push-metrics` (Linux/macOS) or `.\push-metrics.ps1` (Windows), then wire up
   the auto-start mechanism for the platform.
5. The device appears in the `$device` selector on the `Device Aggregate`
   dashboard within ~30 s.

Sanity-check the exposition text without pushing:

```bash
./push-metrics            # ctrl-c after the first "Pushed N metrics"
# or, no push at all:
python3 agent.py --dry-run
```

## Metrics collected

| Metric | Notes |
| :--- | :--- |
| `node_cpu_seconds_total` | Per-core CPU time — **cumulative counter** (Prometheus does the `rate()`) |
| `node_memory_*` | Total / free / available / swap (gauges); `Buffers`/`Cached` Linux-only |
| `node_filesystem_*` | Per-mountpoint size / free / avail, with `fstype` label (auto-detected) |
| `node_disk_*` | Disk I/O bytes and time (counters) |
| `node_network_*` | Per-interface + aggregate throughput (counters) |
| `node_hwmon_temp_celsius` | Temperatures — **Linux:** hwmon; **Windows:** LibreHardwareMonitor; **macOS:** `macmon` (opt-in), else absent |
| `node_load1/5/15` | Load averages (emulated on Windows) |
| `node_time_seconds`, `node_boot_time_seconds` | Clock / uptime |
