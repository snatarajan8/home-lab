# Monitoring Strategy: Netdata to Prometheus/Grafana

## Context
As the home-lab grows, monitoring the resource usage (CPU, RAM, Disk, Network) of the Ryzen Halo host and its containers is critical to avoid resource contention, especially when running large LLMs.

## Decision
We will adopt an **Evolutionary Monitoring Strategy**. We will start with **Netdata** for immediate, low-overhead visibility and migrate to a **Prometheus/Grafana** stack as the complexity of the lab increases.

## Rationale

### Phase 1: Netdata (Current)
*   **Goal:** Immediate visibility with minimal resource "tax."
*   **Pros:** 
    *   Extremely low memory footprint.
    *   Zero configuration required.
    *   Provides high-resolution, real-time metrics.
*   **Cons:** Limited long-term historical analysis and harder to unify into a single "fleet-wide" dashboard.
*   **Why now:** We need to establish a resource baseline to understand how much headroom remains for LLM workloads without committing significant RAM to a complex monitoring stack.

### Phase 2: Prometheus + Grafana (Future)
*   **Goal:** Professional-grade, unified observability.
*   **Pros:** 
    *   Industry standard for DevOps.
    *   Powerful long-term data retention and complex querying.
    *   Highly customizable, beautiful dashboards.
*   **Cons:** Higher resource overhead (RAM/CPU) due to multiple components (Exporter, Database, GUI).
*   **Trigger for Migration:** When the number of managed services exceeds the capacity of a single-host view, or when long-term historical trending becomes a requirement.

## Implementation Plan
1.  Deploy Netdata via `docker-compose` in `services/netdata/`.
2.  Use Netdata to monitor the impact of LLM workloads on the Ryzen Halo.
3.  Evaluate resource headroom before considering the migration to the "Pro Stack."
