# Technical Analysis: PC Agent Pushes No Temperature Metrics

## 1. Executive Summary

The `pc-agent` (`services/monitoring/pc-agent/`) collects CPU, memory, disk, network and
load metrics correctly, but emits **zero** temperature series. The `Device Aggregate`
dashboard's "Max Temperature" / "Temperature Trend" / "All Sensors" panels are permanently
empty for `job="pc_agent"` devices.

Verified against the live stack (`http://amd-halo:9090`):

```
# every temperature series in Prometheus is job="node_exporter" (the Halo itself):
node_hwmon_temp_celsius{job="pc_agent"}   => (empty)

# the pc-agent device is present and healthy for everything else:
{job="pc_agent"} => node_cpu_seconds_total, node_load1, node_memory_*,
                    node_filesystem_*, node_disk_*, node_network_* ... but no temp
```

Root cause: the agent runs **inside WSL2**, and WSL2 does not expose the physical
machine's thermal sensors. The two collection paths in `collect_temperature()` both
dead-end on this hardware.

## 2. Environment

| Fact | Evidence |
| :--- | :--- |
| Agent device | `device="Cracked-ITX"`, `job="pc_agent"` |
| Runs in WSL2 (not Windows-native) | `node_load1{job="pc_agent"} = 0.02` — Linux-style load average; `os.getloadavg()` only succeeds on Linux |
| Reports the WSL virtual disk, not Windows `C:` | `node_filesystem_size_bytes{mountpoint="/"} = 1.08 TB` — the ext4 `.vhdx` dynamic size, not the physical NVMe |
| Collector | `agent.py::collect_temperature()` (added in `a6c02b8`, "add Windows temperature support via PowerShell WMI") |

## 3. Why Both Collection Paths Fail

`collect_temperature()` tries two sources in order:

### Path 1 — `psutil.sensors_temperatures()` (lines 170–186)

WSL2 is a lightweight utility VM running Microsoft's own kernel. It has **no ACPI
thermal zones and no hwmon devices for the host hardware**:

- `/sys/class/thermal/` is empty (no `thermal_zone*`).
- `/sys/class/hwmon/` is absent or empty.
- `psutil.sensors_temperatures()` therefore returns `{}` (or only entries with
  `current <= 0`, which the code filters out).

This is by design — WSL2 virtualises the machine and does not pass through
`coretemp` / `k10temp` / `nvme` / `amdgpu` sensor devices. There is no WSL
configuration that changes this; the physical sensors live on the Windows side.

### Path 2 — PowerShell WMI `MSAcpi_ThermalZoneTemperature` (lines 188–216)

The fallback shells out to `powershell.exe` and queries
`MSAcpi_ThermalZoneTemperature` from the `root/WMI` namespace. This class is the
**ACPI thermal zone** interface, and on this hardware it produces nothing usable:

- Most modern desktop motherboards (this one included — a custom ITX AMD build)
  either do not implement an ACPI thermal zone at all, or expose a single
  coarse "system" zone. Querying the class commonly returns
  `Get-CimInstance : Not supported` (`0x8004100C`) or an empty result.
- `MSAcpi_ThermalZoneTemperature` is *not* a CPU package sensor. Even where it
  responds, it reports an ACPI-defined zone that rarely corresponds to
  `Tctl`/`Tdie`, the iGPU, or the NVMe drive — the sensors the dashboard is
  designed around (see `decisions/dashboard-observability-depth.md` §"Per-sensor
  temperature").
- Reading full WMI/CIM sensor data can additionally require an elevated shell,
  which the agent does not have.

Net result on this PC: Path 1 returns empty, Path 2 returns empty (or errors and
is swallowed by the blanket `except ... Exception`), so `collect_temperature()`
returns `[]`.

## 4. The Deeper Problem: the "WSL-only" Premise Is Broken

`docs/monitoring/pc-metric-collector-agent.md` chose **WSL-only** collection with
this stated rationale:

> "Temperature and load averages are only available on Linux/WSL. A Windows-native
> agent would have reduced functionality..."
> "GPU temperature is available via WSL's `/sys/class/thermal`."

That is factually wrong for temperature. WSL2 **cannot** see host thermal sensors
via `/sys/class/thermal` — that path is empty. The one metric family the WSL-only
decision was made to protect is exactly the one that does not survive the WSL
boundary. Additional collateral from running in WSL:

- **Disk** metrics describe the WSL `.vhdx`, not the real Windows volumes.
- **Network** counters are the WSL virtual NIC, not the physical adapter.
- **CPU / memory / load** are the only metrics that pass through cleanly (WSL2
  shares the host scheduler and RAM).

So the WSL-only approach is not just missing temperature — it is quietly
misreporting disk and network too. A correct fix has to move temperature (at
least) to a Windows-native source.

## 5. What Actually Works on Windows

| Source | Gets real CPU/GPU/SSD temps? | Notes |
| :--- | :--- | :--- |
| `psutil` on Windows-native Python | **No** | psutil has never implemented `sensors_temperatures()` on Windows — raises `AttributeError`. |
| `MSAcpi_ThermalZoneTemperature` (WMI) | Rarely / partially | ACPI zone only; unsupported on many desktops; not per-component. |
| `Win32_PerfFormattedData_Counters_ThermalZoneInformation` | Rarely | Same ACPI-zone limitation. |
| `windows_exporter` `thermalzone` collector | Rarely | Wraps the same ACPI thermal zone. |
| **LibreHardwareMonitor** (LHM) | **Yes** | Reads `k10temp`/`coretemp`, GPU, NVMe, board sensors directly. Exposes a `root/LibreHardwareMonitor` WMI namespace **and** an optional built-in HTTP JSON endpoint (`/data.json`). De-facto standard; MPL-2.0. Requires the LHM process/service running (admin for full sensor set). |
| OpenHardwareMonitor | Yes (older) | Predecessor of LHM; `root/OpenHardwareMonitor` WMI namespace; less actively maintained, weaker Zen/AM5 coverage. |

Conclusion: reliable Windows temperature requires a helper that talks to the SMBus/
Super-I/O chips directly — in practice **LibreHardwareMonitor**. The agent then
reads from LHM (WMI or HTTP) instead of trying to read sensors itself.

## 6. Recommended Direction (details in the decision doc)

1. Move the PC agent to **Windows-native Python** (drop the WSL requirement), or
   run a hybrid where only temperature comes from the Windows side.
2. Use **LibreHardwareMonitor** as the Windows temperature source, read over its
   local HTTP `/data.json` (no elevation needed by the agent itself) or its WMI
   namespace.
3. Make `collect_temperature()` degrade loudly (log at WARNING when no sensor
   source is reachable) instead of silently returning `[]`.
4. Replace the blanket `except (... , Exception)` on the WMI path with specific
   exceptions so real errors are visible.

Full options analysis, including the cross-platform (macOS) implications, is in
`decisions/cross-platform-metric-agent.md`.

## 7. Dashboard Note

`services/monitoring/dashboards/device_aggregate.json` is already correct — panels
5, 8 and 24 query `node_hwmon_temp_celsius{instance=~"$device"}` and will populate
automatically once the agent pushes those series. Panel 5 ("Max Temperature")
uses `max by (instance)` with no sensor-label join, so it will show a bare number;
consider joining `node_hwmon_sensor_label` for a friendly "hottest sensor" readout,
consistent with `temperature_detail.json`. No dashboard change is *required* for
the fix — the gap is entirely agent-side.
