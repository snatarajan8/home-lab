---
name: monitoring-dashboard-failure
description: Investigation into empty Glances metrics and missing new dashboards
metadata:
  type: project
---

# Issue: Monitoring Dashboard Failures

## Problem Statement

Two distinct issues have been identified in the monitoring stack:

1.  **Missing Dashboards**: The newly created dashboards (`system_overview.json` and `system_trends.json`) are not appearing in Grafana.
    - **Cause**: Investigation shows Grafana error logs stating `Dashboard title cannot be empty`. This indicates the JSON files are being found but are invalid because they lack a top-level `"title"` field.
    - **Secondary Cause**: There is confusion in the directory structure and volume mounts between `services/monitoring/dashboards/` and `services/monitoring/provisioning/dashboards/`.

2.  **Empty "Top Processes" Panel**: In the existing `Ryzen Halo Monitoring` dashboard, the panel intended to show top processes via Glances is returning no data.
    - **Potential Cause**: The metric `glances_process_cpu_usage` might not be correctly exported by the `glances` container or might have a different name in the current version of the exporter.

## Proposed Fix Plan

### Phase 1: Fix Dashboard Provisioning (Immediate)
1.  **Standardize Directory Structure**:
    - Ensure all dashboard JSON files are located in `services/monitoring/dashboards/`.
    - Ensure the Grafana container mounts this directory to `/var/lib/grafana/dashboards`.
2.  **Fix Dashboard JSONs**:
    - Add the missing `"title"` field to `system_overview.json` and `system_trends.json`.
3.  **Correct Provisioning Config**:
    - Update `services/monitoring/provisioning/dashboards/dashboard.yml` to point to `/var/lib/grafana/dashboards`.
4.  **Apply Changes**:
    - Use the `run.sh` script to perform a clean restart of the monitoring stack.

### Phase 2: Debug Glances Metrics (Follow-up)
1.  **Verify Exporter**: Check `glances` container logs to confirm it is successfully running in `--export prometheus` mode.
2.  **Verify Metric Name**: Query the Prometheus API via `curl` to see if `glances_process_cpu_usage` (or a similar metric) actually exists.
3.  **Update Dashboard**: If the metric name has changed, update the `grafana_dashboard.json` with the correct PromQL query.

## Verification
- Verify `system_overview` and `system_trends` appear in the Grafana UI with valid data.
- Verify the `Top Processes` panel in the `Ryzen Halo Monitoring` dashboard is populated.
