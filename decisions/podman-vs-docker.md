# Podman vs. Docker: Decision Record

## Context
As part of the home-lab setup on the Ryzen Halo, we are evaluating the container engine to use for our "Core Stack" (Nginx Proxy Manager, Pi-hole, etc.).

## Tradeoffs

| Feature | Docker | Podman |
| :--- | :--- | :--- |
| **Architecture** | **Daemon-based**: Relies on a central `dockerd` process running as root. | **Daemonless**: Runs containers as direct child processes of the user/shell. |
| **Security** | **Higher Attack Surface**: If the daemon is compromised, the entire host is at risk. | **Rootless-first**: Designed to run without root privileges using user namespaces, providing better isolation. |
| **Reliability** | **Single Point of Failure**: If the daemon crashes, all containers are affected. | **Resilient**: No central daemon to fail; relies on `systemd` for service management. |
| **Service Management** | Managed by the Docker Daemon via restart policies (`--restart`). | Managed by `systemd` (the Linux service manager), treating containers as native OS services. |
| **Ecosystem** | Massive; the industry standard with near-universal support. | Highly compatible; supports most Docker commands and `docker-compose` workflows. |
| **Kubernetes Readiness** | Requires extra tools to translate to K8s. | Native "Pod" support and easy export to Kubernetes YAML manifests. |

## Decision
**Use Podman.**

## Rationale
1.  **Security:** The Ryzen Halo is a primary host. Running services rootlessly minimizes the impact of a potential container escape.
2.  **Architecture:** Using `systemd` to manage containers aligns with Linux best practices and provides more robust service management than a single daemon.
3.  **Future-Proofing:** Podman's native support for Pods and Kubernetes manifests makes it a better stepping stone for more advanced orchestration.
