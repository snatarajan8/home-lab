# Dashboard Observability Depth

## Context

The current dashboards (`System Overview`, `System Trends`) give a good "at a glance" view but not enough to dig deeper on demand. Specifically:

1.  **CPU** is only shown as a single aggregate percentage — no per-core breakdown.
2.  **Temperature** is shown as a single value (`glances_sensors_value{label="Tctl"}`) — not each individual sensor.
3.  **There is no process-level view at all.** Neither dashboard shows which processes are consuming CPU, memory, or disk I/O.

This doc covers the investigation into what's actually available from the running stack and proposes how to close these gaps without cluttering the existing high-level views.

## Investigation Findings

I queried the live stack (`node-exporter`, `prometheus`, `glances` are all currently running) directly to check what's really available, rather than assuming from prior docs.

### Per-core CPU — already available, zero new deployment
`node_cpu_seconds_total` is exposed with a `cpu` label for all **32 threads** (Ryzen AI Max, 16c/32t). The current query (`avg by (instance)(...)`) throws this away. No new component is needed — this is a query/panel change only.

### Per-sensor temperature — already available, zero new deployment, and better than what we use today
`node_exporter`'s hwmon collector is already emitting `node_hwmon_temp_celsius` with per-chip/per-sensor labels, joinable with `node_hwmon_sensor_label` for friendly names:

| chip | chip_name | label | current reading |
| :--- | :--- | :--- | :--- |
| `pci0000:00_0000:00:18_3` | `k10temp` | Tctl (CPU) | 91.1°C |
| `0000:00:08_1_0000:c2:00_0` | `amdgpu` | edge (iGPU) | 81°C |
| `nvme_nvme0` | `nvme` | Composite (SSD) | 63.9°C |
| `thermal_thermal_zone0` | `acpitz` | 5 ACPI zones | up to 90.8°C |
| `r8169_0_bf00...` | r8169 | NIC | 69.5°C |

This is strictly more informative than the Glances-based `Tctl`-only reading the dashboards use today — it already covers CPU, GPU, SSD, chassis, and NIC. I confirmed the GPU reading matches Glances' own `glances_gpu_temperature` exactly (81°C both), so nothing is lost by switching.

### Per-process resource usage — **not actually available today**, corrects a prior decision

[[monitoring-strategy]]'s Phase 4 concluded that Glances' Prometheus exporter would "maintain process-level visibility" as a substitute for `process-exporter`. I tested this against the live `glances` container and it's incorrect: Glances' Prometheus export only emits **aggregate counts** (`glances_processcount_running`, `_sleeping`, `_thread`, `_total`). There is no per-process name/CPU/memory/IO data on the `/metrics` endpoint — the `processlist` plugin's detail simply isn't translated into Prometheus format. Glances *does* have this detail on its own JSON REST API, just not exposed to Prometheus.

I also re-tested the `process-exporter` pull that `TODO.md` flagged as blocked by "registry access errors." The commented-out service in `docker-compose.yml` references `stefanprodan/process-exporter:latest`, which isn't the real image — that name doesn't resolve. I pulled the actual canonical image, `docker.io/ncabatoff/process-exporter:latest` (16.6MB), and it succeeded without issue, so Docker Hub access isn't actually a problem here. The prior "registry access error" was most likely this wrong image name, not a network block. `process-exporter.yml` is already committed and valid (groups every process by `{{.Comm}}`, matches everything) and `prometheus.yml` already has a scrape job for it waiting unused — the wiring was already 90% done.

## Decision 1: Per-Process Resource Visibility

| Option | How | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **A. Enable `process-exporter`** (recommended) | Uncomment the service using `ncabatoff/process-exporter`, keep existing `process-exporter.yml` grouping-by-command config | Verified working image; already-committed config and scrape job just need wiring up; native Prometheus metrics (`namedprocess_namegroup_cpu_seconds_total`, `_memory_bytes`, `_read_bytes_total`/`_write_bytes_total`) enable `topk()` for top-N by any resource; historical trends for free (stored in Prometheus like everything else); single query language/datasource | One more small container (~16MB image, can be resource-capped like the others); needs `SYS_PTRACE`-style access to see other containers'/host processes (mitigated the same way `node-exporter`/`glances` already are — read-only host mounts, capability stripping) |
| **B. Grafana Infinity datasource → Glances REST API** | Add the `yesoreyeram-infinity-datasource` community plugin, point a table panel at `glances:61208/api/4/processlist` | No new container; Glances already computes top-N processes for its own UI | Requires installing an unofficial third-party Grafana plugin (Grafana ships without it); snapshot-only — no historical trend graphing of a given process's usage over time, only current-moment tables; a second query language (JSON path) alongside PromQL; violates the "favor standard, well-supported tools" principle in `agent-guidelines.md` |
| **C. Status quo (`glances_processcount` only)** | Keep counts-only | Zero effort | Doesn't answer the actual question — "which process" is invisible, just "how many processes." Rejected — doesn't meet the requirement. |

**Recommendation: Option A.** It's the standard Prometheus-ecosystem tool, the config is already written and committed, and it was never actually blocked — just misconfigured with a nonexistent image name.

## Decision 2: Temperature Granularity

Switch the temperature queries from `glances_sensors_value{label="Tctl"}` to `node_hwmon_temp_celsius`, broken out per `chip`/`sensor`, labeled via `node_hwmon_sensor_label`. No new deployment — `node_exporter` already emits this. Glances stays deployed (still useful for process counts and any GPU-specific plugins not covered elsewhere) but stops being the temperature source of truth.

## Decision 3: Per-Core CPU Visibility

Add a per-core panel (`node_cpu_seconds_total` broken out by `cpu` label, 32 series) — likely a heatmap or sorted bar gauge rather than a 32-line timeseries, to stay readable. No new deployment.

## Decision 4: Dashboard Information Architecture (the "drill down" ask)

Cramming 32 CPU-core series, ~10 temperature sensors, and multiple top-N process tables into `System Overview`/`System Trends` would overwhelm the high-level view you said is already fine. Proposed structure:

- **`System Overview`** and **`System Trends`** — keep largely as-is (high-level, "at a glance"), just repoint the CPU-aggregate and temperature panels at the corrected queries above (still single aggregate numbers here, not per-core/per-sensor).
- **New `CPU Detail` dashboard** — per-core usage, load average, top-N processes by CPU time.
- **New `Memory & Process Detail` dashboard** — memory/swap trend, top-N processes by memory.
- **New `Temperature Detail` dashboard** — every hwmon sensor broken out per chip, with history.
- **New `Disk & I/O Detail` dashboard** — per-mountpoint usage, top-N processes by disk read/write.
- Each detail dashboard is one click away via a Grafana dashboard-links row added to `System Overview`, so the "digging deep" path is: overview → click → detail, rather than scrolling one increasingly dense page.

Alternative considered: keep two dashboards and add collapsible rows for the detail data. Rejected — it directly works against what you asked for; separate dashboards make "digging deep" an explicit, deliberate action instead of visual clutter on the page you check by default.

## Decision 5: Container-Level Visibility (added at user's request)

Nothing in the current stack monitors *per-container* resource usage — only the host as a whole (`node_exporter`) and OS-level processes (`process-exporter`, once enabled). For a host whose entire purpose is running Docker services, "which container is eating CPU/memory/network" is a distinct and high-value question from "which process is."

| Option | How | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **A. cAdvisor** (recommended) | Add `gcr.io/cadvisor/cadvisor`, scrape it from Prometheus | Purpose-built, standard tool for exactly this (used industry-wide); exposes per-container CPU/mem/network/disk/restart-count natively in Prometheus format; pairs naturally with the existing `container_name` labels already used across this stack | Needs read access to `/var/run/docker.sock` to enumerate containers — a materially more sensitive mount than the read-only `/proc`/`/sys` used elsewhere, since it can read container metadata/env vars (though not create/exec/control containers if mounted read-only); some images want `--privileged`, though there are documented non-privileged configs using targeted mounts (`/sys`, `/var/lib/docker`, `/dev/disk`) instead |
| **B. Skip it** | — | No new privilege surface | Leaves the single biggest blind spot for a dedicated Docker host unaddressed |

**Recommendation: Option A**, mounting the Docker socket **read-only** and avoiding `--privileged` (using the documented non-privileged mount set instead), consistent with the capability-stripping pattern already used for every other container in this stack.

## Final Outcome

Decisions confirmed:

1.  **Top-N size:** 10 processes/containers per resource table.
2.  **Detail dashboard grouping:** the four resource-oriented dashboards from Decision 4 (CPU Detail / Memory & Process Detail / Temperature Detail / Disk & I/O Detail) — each pairs a resource's utilization with its own top consumers, matching standard practice (e.g. Node Exporter Full, USE-method dashboards) and the natural "it's high → who's doing it" workflow.
3.  **`process-exporter`:** approved, no objection raised.
4.  **Container-level visibility:** approved — add a new **`Container Overview`** dashboard (top containers by CPU/memory/network). Implementation ended up using `prometheus-podman-exporter` rather than `cAdvisor` as planned here: `cAdvisor` turned out to be structurally incompatible with this host's rootless Podman (private cgroup namespace blocks it from reading other containers' stats, and the standard `cgroup: host` fix doesn't propagate through Podman's Docker-compat API). `prometheus-podman-exporter` talks to Podman's native API directly instead of the cgroup filesystem, sidestepping the problem. Full root-cause and resolution in `issues/cadvisor-rootless-cgroupns-analysis.md`.

Proceeding to implementation planning (`.claude/plans/`) covering:
- `docker-compose.yml`: uncomment/fix `process-exporter` (correct image), add `cadvisor`.
- Repoint `System Overview`/`System Trends` CPU and temperature queries at the corrected metrics.
- New dashboards: `CPU Detail`, `Memory & Process Detail`, `Temperature Detail`, `Disk & I/O Detail`, `Container Overview` — provisioned the same way as the existing two.
- Dashboard-links row on `System Overview` linking to all five detail dashboards.

## Note (unrelated, not fixed)

While reading prior decisions I noticed `decisions/new-dashboards-metrics.md` has its content duplicated with a stray YAML frontmatter block partway through the file — looks like leftover artifact from an earlier edit, not something intentional. Flagging it; didn't touch it since it's outside this task's scope.
