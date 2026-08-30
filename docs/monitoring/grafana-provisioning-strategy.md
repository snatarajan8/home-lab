# Decision: Grafana Dashboard Provisioning vs. Manual Import

## Context
Currently, the Grafana dashboard is a standalone JSON file that requires manual import by the user. This process is prone to errors, specifically the "Datasource prometheus was not found" error, because the dashboard expects a specific datasource UID that is not automatically present in a fresh Grafana installation.

## Problem Statement
Manual dashboard management is not scalable, is not reproducible via Infrastructure-as-Code (IaC), and creates friction for new deployments.

## Proposed Approaches

### Option 1: Manual Import (Current State)
- **Pros:**
    - Zero configuration overhead in the Docker stack.
    - Simple for one-off uses.
- **Cons:**
    - Not reproducible via IaC.
    - Prone to "Datasource not found" errors.
    - Requires manual user intervention every time the stack is recreated.

### Option 2: Grafana Provisioning (Automated)
- **Pros:**
    - **Full IaC Compliance:** The entire observability stack (metrics, dashboards, and datasource connections) is defined in code.
    - **Zero-Touch Deployment:** New deployments work immediately without manual steps.
    - **Eliminates Errors:** By provisioning the Prometheus datasource with the exact UID (`prometheus`) expected by the dashboard, the "Datasource not found" error is permanently resolved.
    - **Scalability:** Easily add more dashboards or datasources by adding files to the provisioning directories.
- **Cons:**
    - Slightly more complex directory structure in the repository.
    - Requires managing additional configuration files (`datasources.yml`, `dashboards.yml`).

## Recommendation
**Option 2 (Grafana Provisioning)** is the strongly recommended approach. It aligns with the "Hardened Docker" and "Evolutionary Observability" strategies by ensuring the stack is robust, reproducible, and professional-grade.

---

## Implementation Plan (Proposed)

1.  **Restructure `services/monitoring/`**:
    - Create `provisioning/datasources/` and `provisioning/dashboards/`.
    - Create a `dashboards/` directory for the JSON files.
2.  **Configure Provisioning**:
    - `provisioning/datasources/datasource.yml`: Configure the Prometheus datasource with `uid: prometheus`.
    - `provisioning/dashboards/dashboard.yml`: Configure the dashboard provider to scan the `dashboards/` directory.
3.  **Update `docker-compose.yml`**:
    - Mount the `provisioning/` and `dashboards/` directories into the Grafana container.
4.  **Cleanup**:
    - Move the existing `grafana_dashboard.json` into the new `dashboards/` directory.
