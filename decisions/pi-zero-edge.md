---
name: pi-zero-edge
description: Design for Pi Zero as an Edge Tier device
metadata:
  type: project
---

# Decision: Pi Zero (Edge Tier)

## Context
The Pi Zero is a low-power, small-form-factor device that is perfect for specialized, lightweight edge services.

## Proposed Architecture

### 1. Roles
- **DNS Sinkhole:** Running Pi-hole or AdGuard Home for network-wide ad blocking.
- **MQTT Broker:** Running Mosquitto to facilitate communication between IoT devices.

### 2. Implementation
- **OS:** Lightweight Linux (e.g., Raspberry Pi OS Lite).
- **Deployment:** Docker containers or direct installation for maximum efficiency.

### 3. Benefits
- **Low Power:** Minimal electricity consumption.
- **Isolation:** Separates critical network infrastructure from the main compute tier.

## Implementation Roadmap

1.  **Phase 1: Setup**
    - Install OS on Pi Zero.
    - Configure basic networking and SSH.
2.  **Phase 2: Service Deployment**
    - Deploy Pi-hole / AdGuard Home.
    - Deploy Mosquitto.
3.  **Phase 3: Integration**
    - Configure other devices to use the Pi Zero as their DNS server.

**Why:** Provides low-power, specialized services at the edge of the network.

**How to apply:** Use [[pi-zero-edge]] to guide the implementation.
