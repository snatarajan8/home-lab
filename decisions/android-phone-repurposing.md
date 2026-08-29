---
name: android-phone-repurposing
description: Design for repurposing old Android phones
metadata:
  type: project
---

# Decision: Android Phone Repurposing

## Context
Old Android phones can be repurposed as specialized tools for the homelab, providing unique capabilities like built-in cameras and sensors.

## Proposed Roles

### 1. Security Cameras
- **App:** IP Webcam or similar.
- **Use Case:** Streaming video to a central security monitoring system.

### 2. Smart Home Dashboards
- **App:** Home Assistant app.
- **Use Case:** A dedicated, wall-mounted interface for controlling smart home devices.

### 3. Sensor Nodes
- **App:** Termux.
- **Use Case:** Running lightweight Linux tasks or leveraging built-in sensors (accelerometer, etc.) for specialized monitoring.

## Implementation Roadmap

1.  **Phase 1: Assessment**
    - Evaluate existing devices for hardware capability.
2.  **Phase 2: Deployment**
    - Set up devices for their intended roles.
3.  **Phase 3: Integration**
    - Integrate into the broader homelab ecosystem.

**Why:** Provides a cost-effective way to add specialized capabilities to the lab.

**How to apply:** Evaluate existing hardware and implement the most appropriate roles.
