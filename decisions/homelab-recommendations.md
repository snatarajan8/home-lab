# Homelab Setup Recommendations

This document outlines a layered approach to building a homelab using existing hardware.

## Hardware Inventory
- **High-Performance Tier:** 2x PCs, Ryzen Halo (Current Host)
- **Low-Power/Edge Tier:** Pi Zero, Android Phones
- **Client Tier:** Macs (Main & Work), iPhone, iPad

---

## Layer 1: The "Brain" (Heavy Lifters)
*Target Hardware: PCs and Ryzen Halo*

### The Proxmox Route (Recommended for one PC)
Install **Proxmox VE** to turn a physical machine into a hypervisor. This allows running multiple Virtual Machines (VMs) and Containers (LXC) to experiment safely.

### The Docker Host (Target: Ryzen Halo)
Use the Ryzen device as a dedicated **Docker Host** using Docker and Docker Compose. Ideal for:
- **Home Assistant:** Smart home management.
- **Pi-hole / AdGuard Home:** Network-wide ad blocking.
- **Nginx Proxy Manager:** Managing SSL and pretty URLs (e.g., `service.home`).

### The Media/Storage Server (Target: Second PC)
Use a PC with large storage as a **NAS (Network Attached Storage)** using **TrueNAS** or a simple Linux server with **Samba**.

---

## Layer 2: The "Edge" (Small & Specialized)
*Target Hardware: Pi Zero and Android Phones*

### The Pi Zero
- **DNS Sinkhole:** Run **Pi-hole** or **AdGuard Home** here.
- **MQTT Broker:** Run **Mosquitto** to facilitate communication between IoT devices.

### The Android Phones
- **Security Cameras:** Use *IP Webcam* apps to turn old phones into cameras streaming to your servers.
- **Smart Home Dashboards:** Mount an old Android on a wall as a dedicated **Home Assistant** interface.
- **Sensor Nodes:** Use *Termux* to run lightweight Linux tasks or leverage built-in sensors.

---

## Layer 3: The "Interface" (Control & Access)
*Target Hardware: Macs, iPhone, iPad, and Work Mac*

### Remote Access (Essential)
- **Tailscale:** Install on **everything**. This creates a secure, private mesh VPN, allowing you to SSH or access services from your Work Mac or iPhone anywhere in the world without opening router ports.

### The Command Center
- **iPad/iPhone:** Use as the primary mobile dashboard for Home Assistant or monitoring tools like **Grafana**.
- **Macs:** Use as the primary development stations for writing Docker Compose files, Ansible scripts, or managing the lab via SSH.

---

## Immediate Next Steps
1. **Install Tailscale** on the Ryzen device and your main PC.
2. **Set up Docker** on the Ryzen device.
3. **Deploy Nginx Proxy Manager and Pi-hole** as Docker containers.
4. **Migrate Pi-hole to the Pi Zero** once the setup is stable.
