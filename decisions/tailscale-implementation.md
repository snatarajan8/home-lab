---
name: tailscale-implementation
description: Design for implementing Tailscale across the homelab
metadata:
  type: project
---

# Decision: Tailscale Implementation

## Context
Secure remote access to the homelab is essential. Tailscale provides a zero-config, secure mesh VPN that allows access to services from anywhere without opening ports on the router.

## Proposed Architecture

### 1. Deployment
- **Installation:** Install Tailscale on all critical devices (Ryzen Halo, PCs, Macs, mobile devices).
- **Tailscale Funnel (Optional):** For exposing certain services to the public internet securely.

### 2. Benefits
- **Zero Config:** No need for complex VPN setups or port forwarding.
- **Secure:** Uses WireGuard® under the hood for high-performance, encrypted communication.
- **Mesh Networking:** Direct peer-to-peer connections between devices.

## Implementation Roadmap

1.  **Phase 1: Initial Setup**
    - Install Tailscale on the Ryzen Halo and main PC.
    - Verify connectivity between them.
2.  **Phase 2: Full Expansion**
    - Install Tailscale on all other key devices (Macs, mobile devices).
3.  **Phase 3: Advanced Usage**
    - Explore Tailscale Funnel or other advanced features.

**Why:** Provides a secure, easy-to-use, and robust way to access the homelab remotely.

**How to apply:** Follow the roadmap to expand Tailscale coverage across the lab.
