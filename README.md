# Home-Lab Repository

This repository contains the infrastructure-as-code (IaC), configuration, and documentation for the Ryzen Halo home-lab stack.

## General Overview

The lab is built around a "Hardened Docker" model, utilizing Docker to provide stable, performant services while mitigating security risks through strict capability stripping, resource limits, and non-root user identities.

## Repository Structure

*   `services/`: Contains the service definitions and configurations.
    *   `monitoring/`: The Prometheus + Grafana observability stack.
*   `decisions/`: Documentation of architectural choices and strategic pivots.
*   `issues/`: Deep-dive technical analyses of encountered problems.
*   `agent-guidelines.md`: Operational instructions for AI agents working in this repo.

## Running Services

Most services are deployed using Docker Compose. 

### Monitoring Stack

To deploy the monitoring stack:

```bash
cd services/monitoring
docker compose up -d
```

Once running, you can access:
- **Grafana:** `http://<your-host-ip>:3000`
- **Prometheus:** `http://<your-host-ip>:9090`
- **Node Exporter:** `http://<your-host-ip>:9100`
- **Glances (Prometheus Export):** `http://<your-host-ip>:61208`

### General Service Deployment

For other services added to the repository, navigate to their respective directory in `services/` and use:

```bash
docker compose up -d
```

## Documentation & Guidelines

- **Decision Log:** Refer to the `decisions/` directory to understand the "why" behind the current stack configuration.
- **Issue Analysis:** Refer to the `issues/` directory for detailed technical post-mortems on previous challenges.
- **Agent Instructions:** All AI agents must adhere to the guidelines in `agent-guidelines.md`.
