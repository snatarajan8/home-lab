# Metrics Aggregation Strategy

## Context

The current monitoring stack uses a "Pull" model where Prometheus scrapes metrics directly from exporters. While effective for stable, local services, this model becomes difficult to scale as the homelab grows to include edge devices (e.g., Pi Zeros), devices behind NAT, or short-lived batch processes. A centralized mechanism is needed to allow these diverse components to report metrics to the Ryzen Halo.

## Comparison of Approaches

| Approach | How it Works | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **Pull Model** (Current) | Prometheus periodically scrapes targets via HTTP. | • Simple and standard.<br>• Low overhead on the target.<br>• Easy to detect if a target is down. | • Requires targets to be network-reachable by Prometheus.<br>• Difficult for devices behind NAT/firewalls.<br>• Not suitable for ephemeral jobs. |
| **Push Model** (Pushgateway) | Clients push metrics to a central gateway; Prometheus scrapes the gateway. | • Solves reachability issues (devices initiate connection).<br>• Ideal for ephemeral/batch jobs.<br>• Low complexity to implement (simple HTTP POST). | • Metrics can become "stale" if a device goes offline.<br>• Adds a single point of failure/bottleneck.<br>• Requires careful labeling to distinguish devices. |
| **OpenTelemetry (OTel)** | Clients push data to an OTel Collector; Collector exports to Prometheus. | • Industry standard and highly extensible.<br>• Decouples instrumentation from storage.<br>• Supports multiple protocols and backends. | • High complexity and steep learning curve.<br>• Higher resource overhead (memory/CPU).<br>• Often overkill for a small-scale homelab. |

## Selected Strategy: Prometheus Pushgateway

We will implement the **Push Model** using the **Prometheus Pushgateway**.

### Rationale

For a homelab environment, the Pushgateway provides the best balance between capability and simplicity. It directly addresses the primary requirement—allowing edge devices to report metrics without complex networking configurations—while remaining lightweight enough to run alongside existing services.

### Pros of this Selection

*   **Low Barrier to Entry**: New devices can start reporting metrics immediately using simple tools like `curl` or lightweight Python scripts.
*   **Connectivity**: Bypasses networking hurdles (NAT, firewalls) by allowing devices to initiate the connection to the Halo.
*   **Seamless Integration**: Works natively with the existing Prometheus and Grafana stack without requiring new backend technologies.

### Cons of this Selection

*   **Metric Staleness**: If a device stops pushing metrics, the last known values remain in the Pushgateway. We must account for this in Grafana (e.g., by checking timestamps or using specific alert rules).
*   **Label Management**: To enable per-device dashboards, we must ensure all pushed metrics include consistent, unique labels (e.g., `device_name` or `instance`).
*   **Centralized Dependency**: The Pushgateway becomes a critical component for all metric collection.
