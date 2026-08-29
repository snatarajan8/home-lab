# Hardened Docker Strategy: Defense in Depth

## Context
Following the failure of the rootless Podman runtime on the Ryzen Halo host, we are pivoting to a Docker-based containerization model. While Docker provides greater operational ease, it introduces a higher security risk because the Docker daemon runs with root privileges. To mitigate this, we will implement a "Hardened Docker" strategy.

## Decision
We will not treat Docker as a "set it and forget it" replacement for Podman. Instead, we will explicitly implement multiple layers of security within our `docker-compose.yml` definitions to approximate the security benefits of a rootless environment.

## The Hardening Layers

### 1. Least Privilege (User Identity)
* **Principle:** The process inside the container should not run as `root`.
* **Implementation:** We will use the `user:` directive in `docker-compose.yml` to specify a non-privileged UID/GID. We will prefer using the pre-configured non-root users provided by official images (e.g., `grafana`, `postgres`).
* **Goal:** If the application process is compromised, the attacker is trapped in a low-privileged user context.

### 2. Capability Stripping (Linux Capabilities)
* **Principle:** A container should only have the minimum Linux kernel capabilities required to function.
* **Implementation:** We will use `cap_drop: [ALL]` for every service and then selectively add only the necessary capabilities using `cap_add: [...]`.
* **Goal:** Minimize the "toolbox" available to an attacker (e.g., preventing them from performing raw network operations or changing file ownership).

### 3. Filesystem Immutability & Isolation
* **Principle:** Containers should have as little write access to the host as possible.
* **Implementation:**
    * **Read-Only Mounts:** Use the `:ro` flag for all host-to-container mounts that do not require writing (e.g., configuration files, system logs).
    * **No Socket Access:** We will strictly avoid mounting `/var/run/docker.sock` unless absolutely necessary for a management tool.
* **Goal:** Prevent a compromised container from modifying host system files or hijacking the Docker daemon.

### 4. Network Segmentation
* **Principle:** Services should only be able to communicate with the entities they need to.
* **Implementation:** We will move away from a single default bridge and instead define granular Docker networks (e.g., `monitoring-net`, `app-net`) to isolate different functional tiers.
* **Goal:** Limit lateral movement in the event of a breach.

### 5. Resource Governance (DoS Prevention)
* **Principle:** No single container should be allowed to starve the host of resources.
* **Implementation:** Define `deploy: resources: limits:` (CPU and RAM) for every service in the compose files.
* **Goal:** Ensure the stability of the Ryzen Halo host, especially when running heavy LLM workloads.

---

## Implementation Roadmap
1.  **Migration:** Convert existing `podman-compose` files to standard `docker-compose` syntax.
2.  **Hardening:** Apply the five layers above to the `services/monitoring/` stack.
3.  **Verification:** Run the stack and verify service accessibility and resource constraints.
