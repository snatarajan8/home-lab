# Decision: Cross-Platform Metric Agent (Windows temps + macOS support)

## Status

**Approved (2026-08-31).** All four recommended options selected. Implementation
plan: [`.claude/plans/cross-platform-metric-agent.md`](../../.claude/plans/cross-platform-metric-agent.md).

Supersedes the "WSL Standardization" decision in
[`pc-metric-collector-agent.md`](pc-metric-collector-agent.md).

## Context

Two goals, one root cause:

1. **Fix PC temperatures.** The `pc-agent` pushes every metric family *except*
   temperature. Root-caused in
   [`issues/pc-agent-temperature-missing-analysis.md`](../../issues/pc-agent-temperature-missing-analysis.md):
   the agent runs in **WSL2**, which does not expose the host's thermal sensors
   (`/sys/class/thermal` is empty), and the PowerShell `MSAcpi_ThermalZoneTemperature`
   fallback returns nothing on this desktop board. Disk and network metrics are
   also quietly wrong under WSL (they describe the WSL `.vhdx` and virtual NIC).

2. **Add a macOS agent.** Run the same collector on this MacBook (Apple Silicon,
   M1 Pro, macOS 14.6) and other Macs, pushing to the same Pushgateway with the
   same `device` label so the `Device Aggregate` dashboard just works.

Both goals require abandoning the WSL-only premise and making the agent genuinely
cross-platform (Windows-native + macOS + Linux).

## Non-negotiables (from `agent-guidelines.md`)

- **Simplicity** — favour standard, well-supported tools over custom code.
- **Least privilege** — the agent should not require running as root/admin if
  avoidable.
- **Robustness** — degrade loudly, keep pushing the metrics that *do* work.

---

## Decision 1: Agent framework — keep the Python agent, or adopt a standard collector?

| Option | How | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **A. Extend the existing Python + psutil agent** (recommended) | Add `platform`-branching collectors; ship a Windows-native and a macOS path alongside the current Linux one | Reuses everything already built and documented — Pushgateway transport, `device` label convention, `node_*` metric names, `config.yaml`, the `Device Aggregate` dashboard; one small dependency (`psutil`); trivial to read and extend; no new server-side component | We own the platform-specific temperature code; psutil gives us nothing for temps on Windows *or* Apple Silicon, so each needs a helper |
| **B. Telegraf** (`inputs.cpu/mem/disk/net/temp` → `outputs.http` to Pushgateway, or `outputs.prometheus_client` pulled) | Replace the agent with a Telegraf config per platform | Standard, well-maintained, single static binary, huge input catalogue, native Prometheus remote-write | New tool to learn and template; `inputs.temp` uses gopsutil and returns **nothing on Apple Silicon and nothing on Windows without LHM** — same hardware wall, so it does not actually solve the hard part; changes the metric names/labels, breaking existing dashboards unless carefully mapped; heavier footprint |
| **C. Grafana Alloy / OTel Collector** | Push via OTLP → Prometheus | Industry-standard telemetry pipeline | Explicitly rejected as "overkill" in [`metrics-aggregation-strategy.md`](metrics-aggregation-strategy.md); same temperature hardware wall; largest complexity jump |
| **D. Per-platform native exporters** (`windows_exporter`, `node_exporter` textfile, a mac exporter) scraped or pushed | Deploy the OS-native exporter on each device | `windows_exporter` gives real Windows-native disk/net/service metrics | Three different exporters to manage; `windows_exporter` thermalzone collector still only wraps ACPI (no real CPU temp); no maintained macOS node_exporter equivalent; still need Pushgateway shims for NAT'd devices; fragmentation |

**Recommendation: Option A.** Telegraf/Alloy do not remove the actual difficulty
(vendor sensor access on Windows and Apple Silicon still needs a dedicated helper),
and they would churn the metric/label scheme the dashboards depend on. The Python
agent already solved transport, labelling and onboarding; the only real work is
two platform-specific temperature collectors, which is the same work under any
framework.

---

## Decision 2: Windows platform strategy — WSL vs native

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **A. Windows-native Python agent** (recommended) | Real physical disk/NIC metrics; can reach LHM's WMI namespace or HTTP endpoint directly; no WSL prerequisite; load average synthesised from `psutil.getloadavg()` (psutil ≥5.9.4 emulates it on Windows) | psutil has no temp support on Windows → needs LHM (Decision 3); packaging on Windows (venv or a PyInstaller `.exe`) |
| **B. Stay in WSL, add a Windows temp bridge** | Minimal change to what runs today | Keeps the misreported disk/net; needs a Windows-side helper *anyway* to get temps across the boundary; two runtimes to keep alive |
| **C. Hybrid — WSL agent shells to `powershell.exe` for LHM data** | No Windows Python | Fragile cross-boundary calls; still WSL disk/net; worst of both |

**Recommendation: Option B from the old decision is reversed — go Windows-native
(Option A).** The WSL-only rationale ("temps/load only exist on Linux") was
incorrect; WSL is now pure downside for this workload.

---

## Decision 3: Windows temperature source

| Option | Real CPU/GPU/SSD temps? | Notes |
| :--- | :--- | :--- |
| **LibreHardwareMonitor, read over its HTTP `/data.json`** (recommended) | Yes | LHM runs with "Remote Web Server" enabled on `localhost:8085`; agent does a plain HTTP GET and walks the JSON tree for `Temperatures` nodes. Agent needs **no elevation**. LHM itself wants admin for the full sensor set and can run as a scheduled task / service. MPL-2.0, de-facto standard. |
| LibreHardwareMonitor via WMI (`root/LibreHardwareMonitor`) | Yes | No extra port, but querying WMI from Python means `wmi`/`pywin32` or shelling to PowerShell; clunkier than one HTTP GET. |
| `MSAcpi_ThermalZoneTemperature` / `windows_exporter` thermalzone | Rarely | ACPI-zone only; unsupported on this board (see issue doc). Keep only as a last-resort fallback. |
| Bundle `LibreHardwareMonitorLib.dll` + `pythonnet` | Yes | No separate app, but adds a .NET runtime dependency and native DLL shipping — fails the simplicity test. |

**Recommendation: LHM + local HTTP.** Document enabling LHM's web server and
auto-start; the agent GETs `http://localhost:8085/data.json` each cycle, maps
sensors to `node_hwmon_temp_celsius{device,chip,sensor}`, and logs a WARNING if
LHM is unreachable. Optionally keep the ACPI-WMI path as a degraded fallback.

---

## Decision 4: macOS temperature source (Apple Silicon is the hard case)

| Option | Sudoless? | Real temps on Apple Silicon? | Notes |
| :--- | :--- | :--- | :--- |
| **`psutil` + best-effort, temps optional** (recommended baseline) | Yes | No | psutil covers CPU/mem/disk/net/loadavg on macOS cleanly. `psutil.sensors_temperatures()` returns `{}` on Apple Silicon. Ship the agent now; treat temps as a platform capability that may be absent. |
| `sudo powermetrics --samplers smc` | No (needs root) | **No** — the `smc` sampler does not report die temps on Apple Silicon; only `--samplers thermal` gives a *pressure level* (nominal/moderate/heavy), not degrees | Also heavyweight and needs a sudoers entry. |
| `macmon` (Rust, reads private `IOReport`) | **Yes** | Yes — CPU/GPU temp in °C without root | Third-party single binary, actively maintained, MIT. Agent shells to `macmon pipe -s 1` (JSON) and parses. Adds a non-repo binary to install per Mac. |
| Small custom SMC/IOKit helper (Swift/C reading `AppleSMC` keys) | Yes | Yes | We own and compile it — fails simplicity, and Apple Silicon SMC keys are undocumented/model-specific. |
| Intel Macs only: `osx-cpu-temp` / `powermetrics smc` | varies | Yes (Intel) | Not relevant to this M1 machine; note for older Macs. |

**Recommendation:** Ship **Option 1 now** — cross-platform agent with macOS
CPU/mem/disk/net/load, temperature best-effort. Offer **`macmon` as an opt-in
enhancement** (`config.yaml: mac_temp_source: macmon`) for Macs where the user
installs it. Do not gate the agent or the dashboard on Apple Silicon temps.

---

## Decision 5: Packaging & label consistency

- **Metric names/labels unchanged** — every platform pushes `node_*` with
  `device="<hostname>"`, so `Device Aggregate` and `Aggregate` dashboards keep
  working with zero changes.
- **One `agent.py`**, platform dispatch via `platform.system()`. Collectors that
  can't run on a platform return `[]` and log once at WARNING.
- **`config.yaml`** gains optional `windows_temp_source` / `mac_temp_source`.
- **Launcher:** a single platform-agnostic `bootstrap.py` (stdlib only) detects
  the OS, builds the venv, installs `macmon` (macOS) / checks LibreHardwareMonitor
  (Windows), and registers the autostart service — `launchd` on macOS,
  `systemd --user` on Linux, a logon Scheduled Task on Windows. `--foreground`
  and `--uninstall` modes. (Supersedes the earlier per-platform
  `push-metrics` / `push-metrics.ps1` / `install-macos.sh` scripts.)
- **Robustness fix:** replace the blanket `except (..., Exception)` in
  `collect_temperature()` with specific exceptions; add a startup self-check that
  logs which collectors are active.

---

## Proposed Final Outcome (pending approval)

1. Reverse WSL-only → **cross-platform Windows-native + macOS + Linux** Python agent.
2. **Windows temps:** LibreHardwareMonitor via local HTTP `/data.json`.
3. **macOS temps:** best-effort now; optional `macmon` integration.
4. No dashboard schema changes required; minor optional polish to
   `device_aggregate.json` panel 5 (join `node_hwmon_sensor_label`).
5. Update `pc-metric-collector-agent.md` and `.claude/plans/pc-metric-collector.md`
   to point here for the platform decision.

## Resolved questions (2026-08-31)

1. **Windows temp source:** LibreHardwareMonitor via local HTTP `/data.json`. ✅
2. **Windows platform:** move fully to Windows-native Python; WSL path retired
   (no parallel transition period). ✅
3. **macOS temps:** ship without Apple Silicon temps; `macmon` opt-in via
   `mac_temp_source: macmon`. Dashboard does not depend on Mac temps. ✅
4. **Scope:** full cross-platform rework in one pass — fix temps, correct the
   WSL-misreported disk/network by going native, add the macOS agent. ✅
