# Monitoring Strategy: Netdata to Prometheus/Grafana

## Context
As the home-lab grows, monitoring the resource usage (CPU, RAM, Disk, Network) of the Ryzen Halo host and its containers is critical to avoid resource contention, especially when running large LLMs.

## Decision
We will adopt an **Evolutionary Monitoring Strategy**. We will start with **Netdata** for immediate, low-overhead visibility and migrate to a **Prometheus/Grafana** stack as the complexity of the lab increases.

## Rationale

### Phase 1: Netdata (Current)
* **Goal:** Immediate visibility with minimal resource "tax."
* **Pros:** 
    * Extremely low memory footprint.
    * Zero configuration required.
    * Provides high-resolution, real-time metrics.
* **Cons:** Limited long-term historical analysis and harder to unify into a single "fleet-wide" dashboard.
* **Why now:** We need to establish a resource baseline to understand how much headroom remains for LLM workloads without committing significant RAM to a complex monitoring stack.

### Phase 2: Prometheus + Grafana (Future)
* **Goal:** Professional-grade, unified observability.
* **Pros:** 
    * Industry standard for DevOps.
    * Powerful long-term data retention and complex querying.
    * Highly customizable, beautiful dashboards.
* **Cons:** Higher resource overhead (RAM/CPU) due to multiple components (Exporter, Database, GUI).
* **Trigger for Migration:** When the number of managed services exceeds the capacity of a single-host view, or when long-term historical trending becomes a requirement.

---

## Pivot: Netdata to Glances

### Problem with Netdata
During implementation, Netdata failed to start in a rootless Podman environment. The error `failed to create new hosts file: open /etc/hosts: permission denied` occurred because Netdata's container entrypoint attempts to perform system-level configuration tasks (like managing users and writing to `/etc`) that conflict with the security boundaries of Podman's user namespaces.

### Why Glances is a better choice for this environment
* **Architectural Simplicity:** Glances is a lightweight, process-based monitor rather than a heavy-duty system integrator. It focuses on reading system state from `/proc` and `/sys` and serving it via a web interface.
* **Rootless Compatibility:** Unlike Netdata, Glances does not attempt to perform administrative tasks (like `usermod` or deep system configuration) within its container. This makes it highly compatible with the permission constraints of rootless Podman.
* **Resource Efficiency:** It has a smaller memory and CPU footprint, which is critical for maintaining headroom for LLM workloads on the Ryzen Halo.
