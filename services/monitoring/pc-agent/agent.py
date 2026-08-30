#!/usr/bin/env python3
"""
Halo Metric Agent — pushes system metrics to Prometheus Pushgateway.

Runs on WSL/Linux. Collects CPU, memory, disk, network, temperature, and load
metrics using psutil, formats them in Prometheus exposition text, and POSTs to
the Pushgateway on the Halo server.

Usage:
    python3 agent.py                  # uses config.yaml in same directory
    python3 agent.py -c /path/to/config.yaml
"""

import argparse
import time
import logging
import os
import socket
import sys
from http.client import HTTPConnection, HTTPStatus
from urllib.parse import urlparse

import psutil
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("halo-agent")


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)

    if "device_name" not in cfg:
        cfg["device_name"] = socket.gethostname()
        log.info("No device_name in config, inferred: %s", cfg["device_name"])

    cfg.setdefault("pushgateway_url", "http://localhost:9091")
    cfg.setdefault("push_interval", 15)
    cfg.setdefault("metrics", {})
    cfg["metrics"].setdefault("cpu", True)
    cfg["metrics"].setdefault("memory", True)
    cfg["metrics"].setdefault("disk", True)
    cfg["metrics"].setdefault("network", True)
    cfg["metrics"].setdefault("temperature", True)
    cfg["metrics"].setdefault("load", True)
    cfg["metrics"].setdefault("disk_paths", ["/"])
    return cfg


def escape_label_value(v: str) -> str:
    """Escape special characters for Prometheus label values."""
    return v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def collect_cpu(device: str) -> list[str]:
    lines = []
    times = psutil.cpu_times(percpu=False)
    interval = psutil.cpu_times_percent(interval=0, percpu=False)

    modes = ["user", "system", "idle", "iowait", "irq", "softirq", "steal"]
    for mode in modes:
        if hasattr(times, mode):
            cumulative = getattr(times, mode)
            lines.append(
                f'node_cpu_seconds_total{{device="{device}",cpu="total",mode="{mode}"}} {cumulative:.2f}'
            )

    percpu_times = psutil.cpu_times(percpu=True)
    for i, cpu_times in enumerate(percpu_times):
        for mode in modes:
            if hasattr(cpu_times, mode):
                cumulative = getattr(cpu_times, mode)
                lines.append(
                    f'node_cpu_seconds_total{{device="{device}",cpu="{i}",mode="{mode}"}} {cumulative:.2f}'
                )

    return lines


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


def collect_disk(device: str, paths: list[str]) -> list[str]:
    lines = []
    seen = set()
    for path in paths:
        try:
            usage = psutil.disk_usage(path)
        except (OSError, PermissionError):
            continue
        key = (usage.total, usage.used, usage.free)
        if key in seen:
            continue
        seen.add(key)
        mp = path.rstrip("/") or "/"
        lines.append(f'node_filesystem_size_bytes{{device="{device}",mountpoint="{mp}"}} {usage.total}')
        lines.append(f'node_filesystem_free_bytes{{device="{device}",mountpoint="{mp}"}} {usage.free}')
        lines.append(f'node_filesystem_avail_bytes{{device="{device}",mountpoint="{mp}"}} {usage.free}')

    io = psutil.disk_io_counters()
    if io:
        lines.append(f'node_disk_read_bytes_total{{device="{device}"}} {io.read_bytes}')
        lines.append(f'node_disk_written_bytes_total{{device="{device}"}} {io.write_bytes}')
        lines.append(f'node_disk_read_time_seconds_total{{device="{device}"}} {io.read_time / 1000:.2f}')
        lines.append(f'node_disk_write_time_seconds_total{{device="{device}"}} {io.write_time / 1000:.2f}')

    return lines


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


def collect_temperature(device: str) -> list[str]:
    lines = []
    try:
        temps = psutil.sensors_temperatures()
    except (AttributeError, OSError):
        return lines

    for chip_name, entries in temps.items():
        for entry in entries:
            if entry.current is not None and entry.current > 0:
                sensor = escape_label_value(entry.label or "unknown")
                chip = escape_label_value(chip_name)
                lines.append(
                    f'node_hwmon_temp_celsius{{device="{device}",chip="{chip}",sensor="{sensor}"}} {entry.current:.1f}'
                )
    return lines


def collect_load(device: str) -> list[str]:
    try:
        load1, load5, load15 = os.getloadavg()
        return [
            f'node_load1{{device="{device}"}} {load1:.2f}',
            f'node_load5{{device="{device}"}} {load5:.2f}',
            f'node_load15{{device="{device}"}} {load15:.2f}',
        ]
    except (OSError, AttributeError):
        return []


def collect_uptime(device: str) -> list[str]:
    boot = psutil.boot_time()
    uptime = time.time() - boot
    return [f'node_time_seconds{{device="{device}"}} {time.time():.0f}',
            f'node_boot_time_seconds{{device="{device}"}} {boot:.0f}']


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
        lines.extend(collect_disk(device, metrics.get("disk_paths", ["/"])))
    if metrics.get("network"):
        lines.extend(collect_network(device))
    if metrics.get("temperature"):
        lines.extend(collect_temperature(device))
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
        if resp.status in (HTTPStatus.OK, HTTPStatus.NO_CONTENT):
            return True
        log.warning("Pushgateway returned %d: %s", resp.status, resp.read().decode(errors="replace"))
        return False
    except Exception as e:
        log.error("Failed to push metrics: %s", e)
        return False
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Halo Metric Agent")
    parser.add_argument("-c", "--config", default=None, help="Path to config.yaml")
    args = parser.parse_args()

    if args.config:
        config_path = args.config
    else:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")

    cfg = load_config(config_path)
    log.info("Starting agent for device=%s, pushgateway=%s, interval=%ds",
             cfg["device_name"], cfg["pushgateway_url"], cfg["push_interval"])

    while True:
        try:
            body = build_metrics(cfg)
            pushed = push_to_gateway(cfg["pushgateway_url"], "pc_agent", cfg["device_name"], body)
            if pushed:
                metric_count = body.count("\n")
                log.info("Pushed %d metrics", metric_count)
            else:
                log.warning("Push failed, will retry next interval")
        except Exception as e:
            log.error("Collection error: %s", e)

        time.sleep(cfg["push_interval"])


if __name__ == "__main__":
    main()
