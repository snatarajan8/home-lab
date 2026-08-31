#!/usr/bin/env python3
"""
Homelab Metric Agent — pushes system metrics to the Prometheus Pushgateway.

Runs natively on Windows, macOS, and Linux. Collects CPU, memory, disk, network,
temperature, and load metrics using psutil (plus a platform-specific temperature
source), formats them in Prometheus exposition text, and PUTs them to the
Pushgateway on the Halo server.

Temperature sources by platform:
    Linux    — psutil.sensors_temperatures() (hwmon / coretemp / k10temp / nvme)
    Windows  — LibreHardwareMonitor's local web server (http://localhost:8085/data.json)
    macOS    — macmon (opt-in; Apple Silicon has no psutil sensor support)

Usage:
    python3 agent.py                       # uses config.yaml in same directory
    python3 agent.py -c /path/to/config.yaml
    python3 agent.py --dry-run             # print exposition text, don't push
"""

import argparse
import json
import logging
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from http.client import HTTPConnection
from urllib.parse import urlparse

import psutil
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("metric-agent")

SYSTEM = platform.system()  # "Linux" | "Windows" | "Darwin"

# Track one-time warnings so a permanently-unavailable collector logs once, not
# every push interval.
_warned: set = set()


def warn_once(key: str, msg: str, level: int = logging.WARNING) -> None:
    if key not in _warned:
        _warned.add(key)
        log.log(level, msg)


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        cfg = yaml.safe_load(f) or {}

    if "device_name" not in cfg:
        cfg["device_name"] = socket.gethostname()
        log.info("No device_name in config, inferred: %s", cfg["device_name"])

    cfg.setdefault("pushgateway_url", "http://localhost:9091")
    cfg.setdefault("push_interval", 15)
    cfg.setdefault("job", "pc_agent")
    cfg.setdefault("windows_temp_source", "lhm")  # "lhm" | "acpi" | "none"
    cfg.setdefault("lhm_url", "http://localhost:8085/data.json")
    cfg.setdefault("mac_temp_source", "none")  # "macmon" | "none"

    cfg.setdefault("metrics", {})
    cfg["metrics"].setdefault("cpu", True)
    cfg["metrics"].setdefault("memory", True)
    cfg["metrics"].setdefault("disk", True)
    cfg["metrics"].setdefault("network", True)
    cfg["metrics"].setdefault("temperature", True)
    cfg["metrics"].setdefault("load", True)
    # disk_paths: omitted / empty  => auto-detect real filesystems
    cfg["metrics"].setdefault("disk_paths", [])
    return cfg


def escape_label_value(v: str) -> str:
    """Escape special characters for Prometheus label values."""
    return v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


# --- CPU --------------------------------------------------------------------

# psutil.cpu_times() field names vary by platform:
#   Linux:   user, nice, system, idle, iowait, irq, softirq, steal, guest, ...
#   Windows: user, system, idle, interrupt, dpc
#   macOS:   user, nice, system, idle
_CPU_MODES = [
    "user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal",
    "interrupt", "dpc",
]


def collect_cpu(device: str) -> list[str]:
    """Emit node_cpu_seconds_total as a real cumulative counter, per logical
    core, mirroring node_exporter. Prometheus does the rate() — the agent must
    not."""
    lines = []
    for i, ct in enumerate(psutil.cpu_times(percpu=True)):
        for mode in _CPU_MODES:
            value = getattr(ct, mode, None)
            if value is None:
                continue
            lines.append(
                f'node_cpu_seconds_total{{device="{device}",cpu="{i}",mode="{mode}"}} {value:.2f}'
            )
    return lines


# --- Memory ---------------------------------------------------------------


def collect_memory(device: str) -> list[str]:
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return [
        f'node_memory_MemTotal_bytes{{device="{device}"}} {mem.total}',
        f'node_memory_MemFree_bytes{{device="{device}"}} {mem.free}',
        f'node_memory_MemAvailable_bytes{{device="{device}"}} {mem.available}',
        f'node_memory_Buffers_bytes{{device="{device}"}} {getattr(mem, "buffers", 0)}',
        f'node_memory_Cached_bytes{{device="{device}"}} {getattr(mem, "cached", 0)}',
        f'node_memory_SwapTotal_bytes{{device="{device}"}} {swap.total}',
        f'node_memory_SwapFree_bytes{{device="{device}"}} {swap.free}',
    ]


# --- Disk ---------------------------------------------------------------


_PSEUDO_FSTYPES = {
    "tmpfs", "devtmpfs", "devfs", "overlay", "squashfs", "aufs", "proc",
    "sysfs", "autofs", "cgroup", "cgroup2", "pstore", "bpf", "tracefs",
    "debugfs", "mqueue", "hugetlbfs", "ramfs", "fuse.gvfsd-fuse", "none", "",
}


def _auto_disk_partitions() -> list[tuple[str, str]]:
    """Return [(mountpoint, fstype)] for real, browsable filesystems."""
    out = []
    for part in psutil.disk_partitions(all=False):
        fstype = (part.fstype or "").lower()
        if fstype in _PSEUDO_FSTYPES:
            continue
        opts = (part.opts or "").split(",")
        # macOS: skip hidden system volumes (/System/Volumes/*, temp mounts)
        if "dontbrowse" in opts or "nobrowse" in opts:
            continue
        # macOS: skip read-only app disk images under /Volumes; keep real drives
        if part.mountpoint.startswith("/Volumes/") and "ro" in opts:
            continue
        out.append((part.mountpoint, part.fstype or "unknown"))
    return out


def collect_disk(device: str, paths: list[str]) -> list[str]:
    lines = []

    if paths:
        targets = [(p, "unknown") for p in paths]
    else:
        targets = _auto_disk_partitions()

    seen = set()
    for mountpoint, fstype in targets:
        try:
            usage = psutil.disk_usage(mountpoint)
        except (OSError, PermissionError):
            continue
        key = (usage.total, usage.used, usage.free)
        if key in seen:
            continue
        seen.add(key)
        mp = escape_label_value(mountpoint)
        ft = escape_label_value(fstype)
        labels = f'device="{device}",mountpoint="{mp}",fstype="{ft}"'
        lines.append(f'node_filesystem_size_bytes{{{labels}}} {usage.total}')
        lines.append(f'node_filesystem_free_bytes{{{labels}}} {usage.free}')
        lines.append(f'node_filesystem_avail_bytes{{{labels}}} {usage.free}')

    io = psutil.disk_io_counters()
    if io:
        lines.append(f'node_disk_read_bytes_total{{device="{device}"}} {io.read_bytes}')
        lines.append(f'node_disk_written_bytes_total{{device="{device}"}} {io.write_bytes}')
        lines.append(f'node_disk_read_time_seconds_total{{device="{device}"}} {io.read_time / 1000:.2f}')
        lines.append(f'node_disk_write_time_seconds_total{{device="{device}"}} {io.write_time / 1000:.2f}')

    return lines


# --- Network ---------------------------------------------------------------


def collect_network(device: str) -> list[str]:
    lines = []
    io = psutil.net_io_counters()
    if io:
        lines.append(f'node_network_receive_bytes_total{{device="{device}"}} {io.bytes_recv}')
        lines.append(f'node_network_transmit_bytes_total{{device="{device}"}} {io.bytes_sent}')
        lines.append(f'node_network_receive_packets_total{{device="{device}"}} {io.packets_recv}')
        lines.append(f'node_network_transmit_packets_total{{device="{device}"}} {io.packets_sent}')

    pernic = psutil.net_io_counters(pernic=True)
    for name, counters in pernic.items():
        escaped = escape_label_value(name)
        lines.append(f'node_network_receive_bytes_total{{device="{device}",interface="{escaped}"}} {counters.bytes_recv}')
        lines.append(f'node_network_transmit_bytes_total{{device="{device}",interface="{escaped}"}} {counters.bytes_sent}')

    return lines


# --- Temperature ---------------------------------------------------------------


def _temp_line(device: str, chip: str, sensor: str, celsius: float) -> list[str]:
    chip = escape_label_value(chip)
    sensor = escape_label_value(sensor)
    return [
        f'node_hwmon_temp_celsius{{device="{device}",chip="{chip}",sensor="{sensor}"}} {celsius:.1f}',
        f'node_hwmon_sensor_label{{device="{device}",chip="{chip}",sensor="{sensor}",label="{sensor}"}} 1',
    ]


def _temp_linux(device: str) -> list[str]:
    try:
        temps = psutil.sensors_temperatures()
    except (AttributeError, OSError):
        temps = {}

    if not temps:
        warn_once("temp-linux", "No hwmon sensors found (psutil.sensors_temperatures empty)")
        return []

    lines = []
    for chip_name, entries in temps.items():
        for entry in entries:
            if entry.current is not None and entry.current > 0:
                lines.extend(
                    _temp_line(device, chip_name, entry.label or "unknown", entry.current)
                )
    return lines


def _lhm_celsius(node: dict) -> "float | None":
    """Extract a temperature in Celsius from an LHM sensor node. Prefers the
    numeric RawValue; falls back to parsing the formatted 'Value' string."""
    raw = node.get("RawValue")
    try:
        c = float(raw)
    except (TypeError, ValueError):
        text = str(node.get("Value", "")).split("°")[0].strip().replace(",", ".")
        try:
            c = float(text)
        except ValueError:
            return None
    if c != c or c <= 0:  # NaN or non-positive
        return None
    return c


def _walk_lhm(node: dict, chip: str, out: list[tuple[str, str, float]]) -> None:
    """Recursively collect (chip, sensor, celsius) from a LibreHardwareMonitor
    /data.json tree. Nodes with a 'HardwareId' key are hardware devices (CPU,
    GPU, SSD, mainboard, sub-chips); temperature sensors carry Type ==
    'Temperature' with a numeric 'RawValue'."""
    if "HardwareId" in node:
        chip = node.get("Text") or chip
    if node.get("Type") == "Temperature":
        celsius = _lhm_celsius(node)
        if celsius is not None:
            out.append((chip or "lhm", node.get("Text", "unknown"), celsius))
    for child in node.get("Children") or []:
        _walk_lhm(child, chip, out)


def _temp_windows(cfg: dict, device: str) -> list[str]:
    source = cfg.get("windows_temp_source", "lhm")
    if source == "none":
        return []

    if source == "lhm":
        url = cfg.get("lhm_url", "http://localhost:8085/data.json")
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError) as e:
            warn_once(
                "temp-lhm",
                f"LibreHardwareMonitor not reachable at {url} ({e}) — no Windows "
                f"temperatures. Install LHM and enable Options > Remote Web Server.",
            )
            return []
        readings: list[tuple[str, str, float]] = []
        _walk_lhm(data, "", readings)
        if not readings:
            warn_once("temp-lhm-empty", f"LHM reachable at {url} but reported no temperature sensors")
        lines = []
        for chip, sensor, celsius in readings:
            lines.extend(_temp_line(device, chip, sensor, celsius))
        return lines

    if source == "acpi":
        return _temp_windows_acpi(device)

    warn_once("temp-win-badsrc", f"Unknown windows_temp_source={source!r}; expected lhm|acpi|none")
    return []


def _temp_windows_acpi(device: str) -> list[str]:
    """Degraded fallback: ACPI thermal zone via WMI. Unsupported on many desktop
    boards — see issues/pc-agent-temperature-missing-analysis.md."""
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "Get-CimInstance MSAcpi_ThermalZoneTemperature -Namespace 'root/WMI' "
             "| Select-Object CurrentTemperature, InstanceName | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            warn_once("temp-acpi", "MSAcpi_ThermalZoneTemperature query failed (not supported on this board)")
            return []
        data = json.loads(result.stdout)
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError, ValueError) as e:
        warn_once("temp-acpi", f"ACPI thermal zone query failed: {e}")
        return []

    if isinstance(data, dict):
        data = [data]

    lines = []
    for zone in data:
        raw_temp = zone.get("CurrentTemperature", 0)
        name = zone.get("InstanceName", "thermal_zone")
        celsius = (raw_temp / 10) - 273.15
        if celsius > 0:
            lines.extend(_temp_line(device, "acpitz", name.split("\\")[-1], celsius))
    return lines


def _temp_macos(cfg: dict, device: str) -> list[str]:
    source = cfg.get("mac_temp_source", "none")
    if source != "macmon":
        warn_once(
            "temp-mac",
            "macOS temperatures disabled. Set mac_temp_source: macmon in config.yaml "
            "and `brew install macmon` to enable (Apple Silicon has no psutil sensor support).",
            level=logging.INFO,
        )
        return []

    # launchd gives jobs a minimal PATH that excludes Homebrew, so fall back to
    # the usual install locations if `macmon` isn't on PATH.
    macmon = shutil.which("macmon")
    for cand in ("/opt/homebrew/bin/macmon", "/usr/local/bin/macmon"):
        if not macmon and os.path.exists(cand):
            macmon = cand
    if not macmon:
        warn_once("temp-mac-missing",
                  "mac_temp_source=macmon but `macmon` not found (try `brew install macmon`)")
        return []

    try:
        result = subprocess.run(
            [macmon, "pipe", "-s", "1", "-i", "200"],
            capture_output=True, text=True, timeout=10,
        )
        # `macmon pipe` prints one JSON object per sample, newline-delimited.
        last = [ln for ln in result.stdout.splitlines() if ln.strip()][-1]
        sample = json.loads(last)
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError, ValueError, IndexError) as e:
        warn_once("temp-macmon", f"macmon read failed: {e}")
        return []

    temp = sample.get("temp", {}) or {}
    lines = []
    for key, sensor in (("cpu_temp_avg", "cpu"), ("gpu_temp_avg", "gpu")):
        val = temp.get(key)
        if isinstance(val, (int, float)) and val > 0:
            lines.extend(_temp_line(device, "soc", sensor, float(val)))
    return lines


def collect_temperature(cfg: dict, device: str) -> list[str]:
    if SYSTEM == "Linux":
        return _temp_linux(device)
    if SYSTEM == "Windows":
        return _temp_windows(cfg, device)
    if SYSTEM == "Darwin":
        return _temp_macos(cfg, device)
    return []


# --- Load / uptime ---------------------------------------------------------------


def collect_load(device: str) -> list[str]:
    try:
        load1, load5, load15 = psutil.getloadavg()
    except (OSError, AttributeError):
        return []
    return [
        f'node_load1{{device="{device}"}} {load1:.2f}',
        f'node_load5{{device="{device}"}} {load5:.2f}',
        f'node_load15{{device="{device}"}} {load15:.2f}',
    ]


def collect_uptime(device: str) -> list[str]:
    boot = psutil.boot_time()
    return [
        f'node_time_seconds{{device="{device}"}} {time.time():.0f}',
        f'node_boot_time_seconds{{device="{device}"}} {boot:.0f}',
    ]


# --- Build / push ---------------------------------------------------------------


def build_metrics(cfg: dict) -> str:
    device = cfg["device_name"]
    metrics = cfg["metrics"]
    lines = []

    lines.extend(collect_uptime(device))

    if metrics.get("cpu"):
        lines.extend(collect_cpu(device))
    if metrics.get("memory"):
        lines.extend(collect_memory(device))
    if metrics.get("disk"):
        lines.extend(collect_disk(device, metrics.get("disk_paths") or []))
    if metrics.get("network"):
        lines.extend(collect_network(device))
    if metrics.get("temperature"):
        lines.extend(collect_temperature(cfg, device))
    if metrics.get("load"):
        lines.extend(collect_load(device))

    return "\n".join(lines) + "\n"


def push_to_gateway(url: str, job: str, instance: str, body: str) -> bool:
    parsed = urlparse(url)
    path = f"/metrics/job/{job}/instance/{instance}"

    conn = HTTPConnection(parsed.hostname, parsed.port or 9091, timeout=10)
    try:
        conn.request("PUT", path, body=body, headers={"Content-Type": "text/plain"})
        resp = conn.getresponse()
        if resp.status in (200, 202, 204):
            return True
        log.warning("Pushgateway returned %d: %s", resp.status, resp.read().decode(errors="replace"))
        return False
    except (OSError, socket.error) as e:
        log.error("Failed to push metrics: %s", e)
        return False
    finally:
        conn.close()


def _temp_source_label(cfg: dict) -> str:
    if not cfg["metrics"].get("temperature"):
        return "off"
    if SYSTEM == "Linux":
        return "hwmon"
    if SYSTEM == "Windows":
        return cfg.get("windows_temp_source", "lhm")
    if SYSTEM == "Darwin":
        return cfg.get("mac_temp_source", "none")
    return "none"


def main():
    parser = argparse.ArgumentParser(description="Homelab Metric Agent")
    parser.add_argument("-c", "--config", default=None, help="Path to config.yaml")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print exposition text to stdout once and exit (no push)")
    args = parser.parse_args()

    config_path = args.config or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "config.yaml"
    )
    cfg = load_config(config_path)

    active = [k for k in ("cpu", "memory", "disk", "network", "temperature", "load")
              if cfg["metrics"].get(k)]
    log.info(
        "Metric agent: device=%s platform=%s job=%s pushgateway=%s interval=%ds",
        cfg["device_name"], SYSTEM, cfg["job"], cfg["pushgateway_url"], cfg["push_interval"],
    )
    log.info("Active collectors: %s | temp source: %s", ",".join(active), _temp_source_label(cfg))

    if args.dry_run:
        sys.stdout.write(build_metrics(cfg))
        return

    while True:
        try:
            body = build_metrics(cfg)
            if push_to_gateway(cfg["pushgateway_url"], cfg["job"], cfg["device_name"], body):
                log.info("Pushed %d metrics", body.count("\n"))
            else:
                log.warning("Push failed, will retry next interval")
        except Exception as e:  # noqa: BLE001 — keep the loop alive on any collector error
            log.error("Collection error: %s", e)

        time.sleep(cfg["push_interval"])


if __name__ == "__main__":
    main()
