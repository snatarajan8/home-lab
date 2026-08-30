# Technical Analysis: cAdvisor Sees No Containers Under Rootless Podman

## 1. Executive Summary

`cadvisor` deploys and runs cleanly (no crashes, registers a "Docker" factory successfully against Podman's Docker-compatible API), but exposes stats for exactly one cgroup — the root (`id="/"`) — and none of the actual containers. The container list/inspect API works correctly; the failure is specifically in cAdvisor's ability to *read the cgroup filesystem for other containers*.

## 2. Root Cause: Private Cgroup Namespace

Rootless Podman gives each container its own **private cgroup namespace** by default. Verified directly:

```
# From inside cadvisor itself:
$ cat /proc/self/cgroup
0::/

# From the host, looking at the same process:
$ cat /proc/<cadvisor-pid>/cgroup
0::/user.slice/user-1001.slice/user@1001.service/user.slice/libpod-<id>.scope/container
```

Inside its own private namespace, cAdvisor's cgroup tree is re-rooted to `/` — it has no visibility into other containers' cgroup paths (e.g. `/user.slice/user-1001.slice/.../libpod-<other-id>.scope`), even though `/sys` is bind-mounted read-only into the container. The mount is correct; the namespace isolation is what hides the content.

## 3. Attempted Fix: `cgroup: host` (Compose Spec)

Docker Compose Spec supports a `cgroup: host` service field for exactly this scenario (join the host's cgroup namespace instead of getting a private one). Added to `docker-compose.yml` and verified via `docker compose up -d cadvisor` — but it had **no effect**: `cadvisor`'s own `/proc/self/cgroup` still reads `0::/` after redeploying with the field set.

This host's `docker`/`docker-compose` are a compatibility shim over Podman (`docker` emulates the Docker CLI via `podman`; `docker-compose` talks to Podman's Docker-API-compatible socket at `/run/user/1001/podman/podman.sock`). The `cgroup: host` field is translated into a Docker `HostConfig.CgroupnsMode: "host"` API field by the Compose client, but Podman's Docker-compat API layer does not appear to honor/translate that field into an actual `--cgroupns=host` container setting. This is a gap in Podman's Docker-API compatibility layer, not a cAdvisor bug — a real, standard Docker Compose directive silently no-ops here.

## 4. What Does Work

Isolating the pieces confirmed the Docker-compat socket itself is fine — it's specifically the cgroup-visibility path that's blocked:

- `curl --unix-socket .../podman.sock http://d/v1.41/containers/json` returns the correct, full container list with real metadata.
- `curl --unix-socket .../podman.sock http://d/v1.41/containers/<id>/json` returns correct inspect data (including `CgroupParent`).
- Only the *stats/cgroup-read* path fails, because it depends on cAdvisor being able to `stat`/`read` files under the reported cgroup path, which its own private namespace hides.

## 5. Is This Fixable Here?

Likely not without a privilege boundary this repo has already deliberately rejected. `[[podman-rootless-permission-denied-analysis]]` documents the same underlying tension for a different symptom (`/etc/hosts` writes) and the same conclusion applies: rootless Podman's user-namespace isolation is a hard OS-level boundary, not something individual container flags can bypass without elevating privilege (e.g. running the container engine as real root), which `[[monitoring-strategy]]`'s "Deep Dive: Why not use `sudo`" section already rejected on security-blast-radius grounds.

A raw `podman run --cgroupns=host` test (bypassing Compose/the Docker-compat layer entirely) was also attempted as a sanity check, but hit the unrelated, already-documented `/etc/hosts` permission wall from `[[podman-rootless-permission-denied-analysis]]` before it could confirm or rule out whether `--cgroupns=host` works at all when Podman is invoked natively — inconclusive, not a dead end in itself.

## 6. Possible Paths Forward (Not Implemented)

- **Podman's native stats API** (`/libpod/containers/{id}/stats` on the same socket, not the Docker-compat surface) — Podman's own process already has legitimate access to its own containers' cgroups without needing an external process to re-derive host paths through a bind mount. A small custom exporter (or a community Podman-native Prometheus exporter, if one exists) hitting this endpoint directly, rather than cAdvisor, may sidestep the namespace problem entirely. Unexplored — flagging as the most promising next step.
- **Native `podman run --cgroupns=host`**, invoked outside the Docker-compat/Compose path — inconclusive per §5, worth a clean retest outside this troubleshooting session.
- **Do nothing further** — accept host-level (`node_exporter`) and process-level (`process-exporter`, now working) visibility as sufficient, and drop per-container breakdown as a non-goal given the environment constraint.

## 7. Resolution: Replaced with `prometheus-podman-exporter`

§6's first suggested path panned out. `quay.io/navidys/prometheus-podman-exporter` is a maintained, dedicated exporter that talks to Podman's **native** libpod API (`/v4.0.0/libpod/containers/stats`) rather than reading the cgroup filesystem — since Podman's own daemon already has direct access to its own containers' stats internally, it never needs to traverse a cgroup path from an external mount, so the private-cgroupns problem in §2 doesn't apply to it at all. `cadvisor` has been removed from `docker-compose.yml` and replaced with this exporter.

Two rootless-specific gotchas hit and fixed along the way, worth keeping in mind for any future container that needs the Podman socket:

1. **No CLI flag for the socket** — despite most examples assuming `--socket`, this build only reads it from the standard `CONTAINER_HOST` env var (same convention the `podman` CLI itself uses), e.g. `CONTAINER_HOST=unix:///run/podman.sock`.
2. **Socket ownership under rootless Podman.** The image's default user is `nobody`, which — like any non-zero UID set inside a rootless container — gets remapped into the subordinate UID range (`/etc/subuid`), landing on some arbitrary host UID that does *not* match the socket file's owner (host UID 1001). Only container UID `0` gets the special identity-mapped treatment back to the invoking host user in Podman's default rootless mapping. Fix: `user: "0:0"` in the compose service. (A third env var, `HOME=/tmp`, was also needed — running as UID 0 with no matching `/etc/passwd` entry left `$HOME` resolving to `/`, which the binary isn't allowed to write a config dir under.)

Verified working: `podman_container_cpu_seconds_total`, `podman_container_mem_usage_bytes`, `podman_container_net_input_total`/`net_output_total` all return real per-container series (joined with `podman_container_info` for human-readable names via `... * on(id) group_left(name) podman_container_info`), for all 6 stack containers.

`cadvisor`'s specific incompatibility (§1–§6 above) stands as documented reference for why it doesn't fit this host, independent of this resolution.
