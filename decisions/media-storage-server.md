---
name: media-storage-server
description: Design for a Media/Storage Server (NAS)
metadata:
  type: project
---

# Decision: Media/Storage Server

## Context
A central storage solution is needed to store media, backups, and other large files. This will be handled by a second PC in the high-performance tier.

## Proposed Architecture

### 1. Hardware Target
- **Second PC:** A machine with high storage capacity (multiple HDDs).

### 2. Operating System & Software
- **Option A: TrueNAS (Scale or Core):**
    - **Pros:** Enterprise-grade, ZFS-native, robust management.
    - **Cons:** More complex to set up and maintain.
- **Option B: Linux Server + Samba/NFS:**
    - **Pros:** Extremely flexible, lightweight, easy to integrate with other Linux services.
    - **Cons:** Requires more manual configuration for storage management and sharing.

### 3. Storage Strategy
- **ZFS:** Recommended for both options to provide data integrity and easy expansion.
- **Redundancy:** RAID-Z1 or RAID-Z2 for data protection.

### 4. Access & Sharing
- **Samba (SMB):** For easy access from Windows, Mac, and mobile devices.
- **NFS:** For high-performance access from other Linux clients/servers.

## Implementation Roadmap

1.  **Phase 1: Setup**
    - Install OS (TrueNAS or Linux).
    - Configure storage pools (ZFS).
2.  **Phase 2: Sharing**
    - Set up Samba/NFS shares.
3.  **Phase 3: Integration**
    - Connect to other services (e.g., Plex/Jellyfin).

**Why:** Provides a centralized, reliable, and high-capacity storage solution.

**How to apply:** Choose between TrueNAS or a Linux server based on the desired complexity and control.
