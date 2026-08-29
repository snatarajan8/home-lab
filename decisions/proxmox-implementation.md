---
name: proxmox-implementation
description: Design for implementing Proxmox VE as a hypervisor in the homelab
metadata:
  type: project
---

# Decision: Proxmox VE Implementation

## Context
To maximize the utility of the high-performance tier (PCs), we need a way to run multiple, isolated workloads. Proxmox VE provides a robust, enterprise-grade virtualization platform that supports both Virtual Machines (VMs) and Linux Containers (LXC), making it ideal for a homelab environment.

## Proposed Architecture

### 1. Hardware Target
- **Primary Host:** Second PC (Large storage capacity).
- **Secondary Host (Optional):** Ryzen Halo (if dedicated to Docker, but could run lightweight LXCs).

### 2. Hypervisor Configuration
- **Installation:** Standard Proxmox VE installation on bare metal.
- **Storage Strategy:**
    - **OS Drive:** SSD (e.g., NVMe) for fast boot and system responsiveness.
    - **Data Storage:** ZFS pool for VMs and LXC containers to provide data integrity, snapshots, and easy scaling.
    - **Bulk Storage:** External or internal HDD pool for media/large files, potentially shared via Samba/NFS.
- **Networking:**
    - **Bridge Networking:** Create a Linux Bridge (`vmbr0`) to allow VMs and LXCs to reside on the same subnet as the physical network.
    - **VLAN Support:** Configure VLAN-aware bridges to isolate different tiers (e.g., IoT, Management, Guest).

### 3. Workload Distribution
- **Virtual Machines (VMs):**
    - Windows/macOS for specific desktop needs.
    - Full OS instances requiring high isolation (e.g., a dedicated Linux distro for testing).
- **Linux Containers (LXCs):**
    - Lightweight services: Pi-hole (if not on Pi Zero), Nginx Proxy Manager, various web servers.
    - Highly efficient for running Linux-based services with minimal overhead.

### 4. Management & Access
- **Web UI:** Primary management via the Proxmox web interface.
- **SSH:** Direct access for CLI administration.
- **API:** For automation and integration with other tools.

### 5. Backup & Disaster Recovery
- **Proxmox Backup Server (PBS):** Deploy PBS (either as a VM or on a separate machine/NAS) for incremental, deduplicated backups.
- **Scheduled Backups:** Implement automated backup schedules for all critical VMs and LXCs.
- **Snapshots:** Utilize ZFS snapshots for quick rollback during experimentation.

## Implementation Roadmap

1.  **Phase 1: Setup**
    - Install Proxmox VE on the target hardware.
    - Configure networking (Bridge, VLANs).
    - Configure storage (ZFS pools).
2.  **Phase 2: Baseline Services**
    - Deploy essential LXCs (e.g., Nginx Proxy Manager, Pi-hole).
    - Set up Proxmox Backup Server.
3.  **Phase 3: Advanced Workloads**
    - Deploy VMs as needed.
    - Integrate with existing monitoring (Grafana/Prometheus).

**Why:** This approach provides a scalable, highly available, and manageable platform for running a wide variety of services, from lightweight containers to full-fledged virtual machines.

**How to apply:** Follow the roadmap to build out the Proxmox environment. Use PBS for all critical workloads.
