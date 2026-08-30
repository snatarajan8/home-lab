---
name: new-dashboards-metrics
description: Decision on metrics and visualization strategy for new monitoring dashboards
metadata:
  type: project
---

# Decision: Monitoring Dashboard Metrics & Visualization

## Context
The current dashboard ("Ryzen Halo Monitoring") provides basic memory usage and top processes via Glances. We need to expand this to include temperatures, CPU usage, and other vital system metrics to provide a holistic view of the home lab's health.

## Proposed Metrics

### 1. CPU (Critical)
*   **Usage % (Total & Per-Core):** To identify single-threaded bottlenecks or overall heavy load.
    *   *Visualization:* `Gauge` for total, `Bar Gauge` or `Timeseries` for per-core.
*   **Load Average (1m, 5m, 15m):** To understand system pressure over time.
    *   *Visualization:* `Timeseries`.
*   **CPU Steal/Wait:** To identify if the host is overcommitted or if I/O is stalling the CPU.
    *   *Visualization:* `Timeseries`.

### 2. Memory (Critical)
*   **Usage (Absolute & %):** To monitor capacity.
    *   *Visualization:* `Stat` for current, `Timeseries` for trends.
*   **Swap Usage:** To see if the system is starting to "thrash".
    *   *Visualization:* `Timeseries`.

### 3. Temperature (Requested)
*   **CPU Package Temperature:** The primary thermal metric.
    *   *Visualization:* `Gauge` or `Stat`.
*   **Core Temperatures:** To detect thermal hotspots.
    *   *Visualization:* `Bar Gauge`.
*   **GPU/Other Sensors:** If available via `node_exporter`.

### 4. Disk (Important)
*   **Disk Usage %:** To prevent "disk full" outages.
    *   *Visualization:* `Bar Gauge` per mount point.
*   **I/O Throughput (Read/Write):** To monitor heavy I/O operations.
    *   *Visualization:* `Timeseries`.

### 5. Network (Important)
*   **Interface Throughput (Rx/Tx):** To monitor network load.
    *   *Visualization:* `Timeseries`.

## Visualization Strategy

| Metric Type | Primary Visualization | Rationale |
| :--- | :--- | :--- |
| **Instantaneous Value** (Current Temp, CPU %) | `Stat` / `Gauge` | High visibility for "at a glance" health. |
| **Trends over time** (CPU usage, Memory, Temp) | `Timeseries` | Essential for identifying patterns or gradual leaks. |
| **Categorical/List** (Top Processes, Disk usage) | `Table` / `Bar Gauge` | Easy to compare multiple items (e.g., which disk is fullest). |

## What to Exclude (Deep Cuts)
*   **Per-core Interrupt counts:** Too noisy for general monitoring.
*   **Extremely granular network packet/byte counts:** Hard to read at scale; throughput is usually sufficient.
*   **Individual CPU frequency (MHz) per core:** Unless doing deep performance tuning, it adds too much visual clutter.

**Why:** This strategy balances actionable insights with visual clarity, avoiding "dashboard fatigue" while ensuring critical system health indicators are prominent.

---
name: new-dashboards-metrics
description: Decision on metrics and visualization strategy for new monitoring dashboards
metadata:
  type: project
---

# Decision: Monitoring Dashboard Metrics & Visualization

## Context
The current dashboard ("Ryzen Halo Monitoring") provides basic memory usage and top processes via Glances. We need to expand this to include temperatures, CPU usage, and other vital system metrics to provide a holistic view of the home lab's health.

## Proposed Metrics

### 1. CPU (Critical)
*   **Usage % (Total & Per-Core):** To identify single-threaded bottlenecks or overall heavy load.
    *   *Visualization:* `Gauge` for total, `Bar Gauge` or `Timeseries` for per-core.
*   **Load Average (1m, 5m, 15m):** To understand system pressure over time.
    *   *Visualization:* `Timeseries`.
*   **CPU Steal/Wait:** To identify if the host is overcommitted or if I/O is stalling the CPU.
    *   *Visualization:* `Timeseries`.

### 2. Memory (Critical)
*   **Usage (Absolute & %):** To monitor capacity.
    *   *Visualization:* `Stat` for current, `Timeseries` for trends.
*   **Swap Usage:** To see if the system is starting to "thrash".
    *   *Visualization:* `Timeseries`.

### 3. Temperature (Requested)
*   **CPU Package Temperature:** The primary thermal metric.
    *   *Visualization:* `Gauge` or `Stat`.
*   **Core Temperatures:** To detect thermal hotspots.
    *   *Visualization:* `Bar Gauge`.
*   **GPU/Other Sensors:** If available via `node_exporter`.

### 4. Disk (Important)
*   **Disk Usage %:** To prevent "disk full" outages.
    *   *Visualization:* `Bar Gauge` per mount point.
*   **I/O Throughput (Read/Write):** To monitor heavy I/O operations.
    *   *Visualization:* `Timeseries`.

### 5. Network (Important)
*   **Interface Throughput (Rx/Tx):** To monitor network load.
    *   *Visualization:* `Timeseries`.

## Visualization Strategy

| Metric Type | Primary Visualization | Rationale |
| :--- | :--- | :--- |
| **Instantaneous Value** (Current Temp, CPU %) | `Stat` / `Gauge` | High visibility for "at a glance" health. |
| **Trends over time** (CPU usage, Memory, Temp) | `Timeseries` | Essential for identifying patterns or gradual leaks. |
| **Categorical/List** (Top Processes, Disk usage) | `Table` / `Bar Gauge` | Easy to compare multiple items (e.g., which disk is fullest). |

## What to Exclude (Deep Cuts)
*   **Per-core Interrupt counts:** Too noisy for general monitoring.
*   **Extremely granular network packet/byte counts:** Hard to read at scale; throughput is usually sufficient.
*   **Individual CPU frequency (MHz) per core:** Unless doing deep performance tuning, it adds too much visual clutter.

**Why:** This strategy balances actionable insights with visual clarity, avoiding "dashboard fatigue" while ensuring critical system health indicators are prominent.

**How to apply:** Use these definitions to create new Grafana dashboard JSON files and update the provisioning configuration.

## Final Outcome
Implemented two dashboards:
1.  `system_overview.json`: High-level `Stat` and `Gauge` panels for instant visibility into CPU, Memory, Temperature, and Disk usage.
2.  `system_trends.json`: `Timeseries` panels for tracking CPU, Memory, Temperature, Disk I/O, and Network throughput over time.

Both dashboards were provisioned into the monitoring stack via the existing dashboard provider configuration.

