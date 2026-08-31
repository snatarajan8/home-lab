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

## Quick start

Install **Python 3** first (`brew install python` / `winget install Python.Python.3.12` /
`apt install python3 python3-venv`), then from this directory:

```bash
python3 bootstrap.py            # deps + install autostart service + start
```

`bootstrap.py` detects the platform and does the rest:

| | what it does |
| :--- | :--- |
| **macOS** | `brew install macmon` if missing (temps); deploys a copy to `~/Library/Application Support/homelab-metric-agent/` (macOS TCC blocks launchd from running code under `~/Desktop`); loads a **launchd** agent |
| **Linux** | warns on WSL / missing hwmon; installs a **`systemd --user`** service that runs from this directory |
| **Windows** | checks LibreHardwareMonitor's web server (temps); deploys a copy to `%LOCALAPPDATA%`; registers a **Scheduled Task** at logon |

```bash
python3 bootstrap.py --foreground   # run now, no service (Ctrl-C to stop)
python3 bootstrap.py --uninstall    # stop + remove the service
python3 bootstrap.py --config PATH  # use a specific config file
python3 agent.py --dry-run          # print the exposition text, don't push
```

The device shows up in the `$device` selector on the `Device Aggregate` dashboard
within ~30 s.

## Config

`config.yaml` is the tracked template. For a real deployment drop a
**`config.local.yaml`** next to it (gitignored) — `bootstrap.py` prefers it, so
machine-specific values never land in git.

```yaml
pushgateway_url: "http://amd-halo:9091"   # required
push_interval: 15
job: "pc_agent"
# device_name: "my-box"                   # optional; defaults to the hostname
                                          # set it if the hostname is ugly (MDM serial)
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
mac_temp_source: "macmon"                  # macmon | none
```

## Per-platform notes

### Linux
Temperature comes from `psutil.sensors_temperatures()` (`coretemp`, `k10temp`,
`nvme`, `amdgpu`, …) — nothing extra to install. To keep the service running
without an active login session:
`sudo loginctl enable-linger <user>`.

### Windows — LibreHardwareMonitor (temperatures)
`psutil` cannot read temperatures on Windows and the ACPI thermal zone is
unsupported on most desktop boards. Install
[LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases),
then **Options →**

- ✔ **Run On Windows Startup**, ✔ **Start Minimized / Minimize To Tray**
- ✔ **Run As Administrator on Startup** (needed for the full sensor set)
- **Remote Web Server → Port 8085**, then ✔ **Run**

Verify <http://localhost:8085/data.json> returns JSON. Without it, set
`windows_temp_source: "acpi"` (degraded) or `"none"`.

`bootstrap.py` registers the agent as a per-user logon task at the **Limited**
run level, so it needs **no elevation** — run it from a normal terminal. If your
account is blocked from creating tasks by policy you'll see
`Register-ScheduledTask : Access is denied`; open an **Administrator** terminal
and re-run `python bootstrap.py` (an elevated run registers the task at the
`Highest` run level). LibreHardwareMonitor still needs its own
"Run As Administrator" setting for the full sensor set — that's independent of
how the agent task runs.

### macOS — macmon (temperatures)
Apple Silicon exposes no sensors to `psutil`.
[`macmon`](https://github.com/vladkens/macmon) is a **sudoless** reader of Apple's
private IOReport API — `bootstrap.py` runs `brew install macmon` for you. You get
two series (`chip="soc"`, `sensor="cpu"|"gpu"`), not per-sensor detail. If macmon
isn't installed the agent just skips temps.

Intel Macs: `macmon` is Apple-Silicon-only; set `mac_temp_source: "none"`
(`powermetrics`/`osx-cpu-temp` are not wired up).

## Metrics collected

| Metric | Notes |
| :--- | :--- |
| `node_cpu_seconds_total` | Per-core CPU time — **cumulative counter** (Prometheus does the `rate()`). On Apple Silicon the per-core tick counters lag ~10–15% when cores park, so CPU% reads a little low. |
| `node_memory_*` | Total / free / available / swap (gauges); `Buffers`/`Cached` Linux-only |
| `node_filesystem_*` | Per-mountpoint size / free / avail, with `fstype` label (auto-detected) |
| `node_disk_*` | Disk I/O bytes and time (counters) |
| `node_network_*` | Per-interface + aggregate throughput (counters) |
| `node_hwmon_temp_celsius` | Temperatures — **Linux:** hwmon; **Windows:** LibreHardwareMonitor; **macOS:** `macmon`, else absent |
| `node_load1/5/15` | Load averages (emulated on Windows) |
| `node_time_seconds`, `node_boot_time_seconds` | Clock / uptime |
