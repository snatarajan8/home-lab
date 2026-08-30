# Halo PC Metric Agent

Lightweight agent that runs on WSL and pushes system metrics to the Prometheus Pushgateway on the Halo server.

## Quick Start

```bash
pip install -r requirements.txt
vim config.yaml          # set pushgateway_url
./push-metrics
```

Device name is inferred automatically from the WSL hostname. No manual configuration needed.

## Config

```yaml
pushgateway_url: "http://<halo-ip>:9091"  # required
push_interval: 15                          # seconds between pushes
metrics:
  cpu: true
  memory: true
  disk: true
  network: true
  temperature: true
  load: true
  disk_paths:
    - "/"
```

## Windows Task Scheduler (auto-start on login)

```powershell
# Run PowerShell as Administrator
$action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument "bash /path/to/pc-agent/push-metrics"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0
Register-ScheduledTask -TaskName "HaloMetricAgent" -Action $action -Trigger $trigger -Settings $settings -Description "Push system metrics to Halo Pushgateway"
```

## Onboarding a New PC

1. Ensure WSL2 is installed: `wsl --install`
2. Copy this directory into the WSL filesystem
3. `sudo apt install python3 python3-pip`
4. `pip install -r requirements.txt`
5. Edit `config.yaml`: set `pushgateway_url` to the Halo's Pushgateway address
6. Run `./push-metrics` or set up the Task Scheduler task above

Device name is auto-detected from the WSL hostname. To override, add `device_name: "custom-name"` to config.yaml.

## Metrics Collected

| Metric | Description |
| :--- | :--- |
| `node_cpu_seconds_total` | Per-core CPU time (counter) |
| `node_memory_*` | Memory usage (gauges) |
| `node_filesystem_*` | Disk usage per mountpoint (gauges) |
| `node_disk_*` | Disk I/O (counters) |
| `node_network_*` | Network throughput (counters) |
| `node_hwmon_temp_celsius` | Temperature sensors (gauges) |
| `node_load*` | Load averages (gauges) |
