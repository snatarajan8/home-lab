---
name: docker-host-ryzen
description: Design for Ryzen Halo as a dedicated Docker Host
metadata:
  type: project
---

# Decision: Docker Host (Ryzen Halo)

## Context
The Ryzen Halo device is a high-performance, low-power device that is ideal for running a dedicated Docker Host. This host will run various essential services for the homelab.

## Proposed Architecture

### 1. Host OS
- **Operating System:** Lightweight Linux distribution (e.g., Debian, Ubuntu Server, or Alpine).
- **Docker Engine:** Docker and Docker Compose for container orchestration.

### 2. Key Services
- **Home Assistant:** Smart home management and automation.
- **Nginx Proxy Manager:** Managing SSL certificates and reverse proxying for various services.
- **Pi-hole / AdGuard Home:** Network-wide ad blocking and DNS management.
- **Monitoring Stack:** Prometheus, Grafana, and Glances for system observability.

### 3. Management & Access
- **SSH:** Secure remote access.
- **Docker Compose:** Declarative management of all services.
- **Nginx Proxy Manager:** Providing pretty URLs (e.g., `homeassistant.home`) and SSL via Let's Encrypt.

### 4. Networking & Security
- **Docker Network:** Using custom bridge networks to isolate services.
- **Reverse Proxy:** All external-facing services should be behind Nginx Proxy Manager.
- **Hardening:** Using `cap_drop: - ALL` and `cap_add` to minimize container privileges where possible.

## Implementation Roadmap

1.  **Phase 1: Foundation**
    - Install OS and Docker.
    - Set up Nginx Proxy Manager.
2.  **Phase 2: Core Services**
    - Deploy Pi-hole / AdGuard Home.
    - Deploy Home Assistant.
3.  **Phase 3: Observability**
    - Deploy the monitoring stack (Prometheus, Grafana, etc.).

**Why:** This approach leverages the Ryzen Halo's strengths for running a reliable and efficient set of core services.

**How to apply:** Use Docker Compose to manage all services and ensure they are organized and easily deployable.
