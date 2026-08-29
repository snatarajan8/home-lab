# Monitoring Stack

This directory contains the Docker-based monitoring stack for the Ryzen Halo host. The stack implements a **Defense in Depth** security strategy to mitigate the risks of running a root-privileged Docker daemon.

## Services

| Service | Role | Endpoint | Hardening Applied |
| :--- | :--- | :--- | :--- |
| **Node Exporter** | Host metrics collection | `http://<host-ip>:9100/metrics` | `cap_drop: [ALL]`, `cap_add: [SYS_TIME]`, Resource limits |
| **Prometheus** | Time-series database | `http://<host-ip>:9090` | `cap_drop: [ALL]`, Resource limits, Read-only config |
| **Grafana** | Data visualization | `http://<host-ip>:3000` | Non-root user (`uid 472`), `cap_drop: [ALL]`, Resource limits |

## Security Architecture

The stack is hardened using the following principles:
- **Least Privilege:** Services run as non-root users where possible.
- **Capability Stripping:** All unnecessary Linux capabilities are dropped.
- **Filesystem Immutability:** Configuration files are mounted as read-only.
- **Resource Governance:** CPU and Memory limits are enforced to prevent host exhaustion.

## Accessing the Dashboard

1. Navigate to `http://<your-tailscale-ip>:3000`.
2. Login with the credentials specified in your `.env` file (Default: `admin` / `[your-password]`).
3. Import a "Node Exporter Full" dashboard to begin visualizing host metrics.
