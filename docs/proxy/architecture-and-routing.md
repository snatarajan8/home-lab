# Architecture Discussion: Site Hosting & Proxy Strategy

## Objective:
Migrate `my-site` from Vercel to the local Ryzen Halo host and establish a secure, professional routing architecture.

## Proposed Architecture

### 1. Hosting
- **Service:** `my-site` (Next.js)
- **Deployment:** Containerized via Docker.
- **Environment:** Ryzen Halo host.

### 2. Routing & Security (The "Front Door")
To allow secure external access to the site and other services, a two-tier routing system is proposed:

#### Tier 1: Cloudflare Tunnel (The Entry Point)
- **Role:** Creates a secure, outbound-only connection from the home lab to the Cloudflare network.
- **Benefit:** Eliminates the need to open inbound ports on the home router, effectively hiding the home IP address and providing native DDoS protection.
- **Configuration:** The tunnel will point all incoming traffic to the local Nginx Proxy Manager instance.

#### Tier 2: Nginx Proxy Manager (The Traffic Controller)
- **Role:** Acts as the internal reverse proxy.
- **Benefit:** 
    - Centralizes all routing rules (e.g., `status.shyamnatarajan.me` $\rightarrow$ `grafana:3000`).
    - Provides a GUI for managing subdomains and SSL certificates via Let's Encrypt.
    - Manages path-based routing and access control.
- **Interaction:** Receiving traffic from the Cloudflare Tunnel, it directs users to the appropriate internal container.

## Summary of Flow
`User` $\rightarrow$ `Cloudflare (DDoS Protection)` $\rightarrow$ `Cloudflare Tunnel` $\rightarrow$ `Nginx Proxy Manager` $\rightarrow$ `Target Service (e.g., my-site, Grafana)`

---
*Document generated on 2026-08-30*
