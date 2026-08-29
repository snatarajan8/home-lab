# Monitoring Strategy: Evolutionary Observability

## Context
As the home-lab grows, monitoring the resource usage (CPU, RAM, Disk, Network) of the Ryzen Halo host and its containers is critical to avoid resource contention, especially when running large LLMs.

## Decision
We will adopt an **Evolutionary Observability** strategy. We will bypass "System-Centric" tools that conflict with rootless container runtimes and move straight to a **Prometheus + Grafana** stack.

## Rationale

### Phase 1: Netdata (Attempted)
* **Goal:** Immediate visibility with minimal resource "tax."
* **Outcome:** **Failed.**
* **Failure Reason:** Netdata's container entrypoint attempts to perform system-level configuration tasks (like managing users and writing to `/etc`) that conflict with the security boundaries of Podman's user namespaces.

### Phase 2: Glances (Attempted)
* **Goal:** Lightweight, rootless-friendly monitoring.
* **Outcome:** **Failed.**
* **Failure Reason:** Even with a stripped-down configuration, the container runtime attempted to create the `/etc/hosts` file, which triggered a permission error due to the way rootless Podman manages the container's identity.

### Phase 3: Prometheus + Grafana (Final Selection)
* **Goal:** Professional-grade, unified observability.
* **Pros:** 
    * **Architectural Decoupling:** Prometheus uses a "Pull" model via HTTP, making it agnostic to the host's filesystem or identity.
    * **Rootless/Docker Compatibility:** By using container-internal DNS (e.g., `node-exporter:9100`), we bypass the host-level `/etc/hosts` permission wall.
    * **Scalability:** Provides a stable, industry-standard foundation for long-term historical analysis.

### Phase 4: Glances as Prometheus Exporter (Final Implementation)
* **Goal:** Process-level observability without the friction of `process-exporter` image availability/permissions.
* **Outcome:** **Successful.**
* **Rationale:** While `process-exporter` was the initial target, persistent "access denied" errors and registry issues made it unreliable in this environment. **Glances** provides a robust, all-in-one alternative that supports a native Prometheus export mode, allowing us to maintain process-level visibility within our existing hardened stack.

---

## Deep Dive: The Rootless/Container Runtime Conflict

During troubleshooting, we encountered a critical failure where even the most minimal container creation failed with `open /etc/hosts: permission denied`. 

As documented in [[podman-rootless-permission-denied-analysis]], this is a fundamental conflict between the OCI runtime (`crun`) and the host's user namespace/filesystem implementation (`fuse-overlayfs`). This error occurs at the most atomic level of container initialization, meaning no amount of configuration within the container itself can bypass it.

**Conclusion:** While the "Rootless" model is architecturally superior for security, the current host environment's implementation of rootless Podman is effectively non-functional for standard container workloads. We have successfully implemented a "Hardened Docker" alternative.

## Deep Dive: Hardened Docker Strategy

To mitigate the increased security risk of running a root-privileged Docker daemon, we implement a **Defense in Depth** approach:

1.  **Least Privilege (User Identity):** We explicitly specify non-root users within containers (e.g., `user: "472"` for Grafana).
2.  **Capability Stripping:** We use `cap_drop: [ALL]` and selectively `cap_add` only what is strictly necessary (e.g., `SYS_TIME` for `node-exporter`).
3.  **Filesystem Immutability:** We utilize read-only mounts (`:ro`) for all host-to-container configuration volumes.
4.  **Network Segmentation:** We use dedicated Docker networks to isolate different service tiers.
5.  **Resource Governance:** We define CPU and memory limits for every service to prevent host resource exhaustion.

---

## Deep Dive: Why not use `sudo`?

During troubleshooting, the option to run containers with `sudo` was considered. This was rejected based on two architectural principles:

1.  **Security (Blast Radius):** Running a web-facing application like Netdata or Glances as `root` creates a massive security risk. A single vulnerability could lead to full host compromise.
2.  **Management Debt:** Using `sudo` breaks the rootless model, leading to complex permission issues when managing files and volumes as a regular user.

**The goal is to build a lab that is secure by design, not one that is "fixed" by bypassing security boundaries.**
