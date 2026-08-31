#!/usr/bin/env python3
"""
bootstrap.py — one command to set up the homelab metric agent on any platform.

    python3 bootstrap.py               # deps + install autostart service + start
    python3 bootstrap.py --foreground  # deps + run in the foreground (no service)
    python3 bootstrap.py --uninstall   # stop and remove the autostart service
    python3 bootstrap.py --config PATH # use a specific config file

Detects Linux / macOS / Windows and does the right thing:

  macOS    installs `macmon` via Homebrew if missing (CPU/GPU temps); deploys a
           self-contained copy to ~/Library/Application Support (macOS TCC blocks
           launchd from running code under ~/Desktop) and loads a launchd agent.
  Linux    warns if running under WSL / no hwmon sensors; installs a
           `systemd --user` service that runs from this directory.
  Windows  checks LibreHardwareMonitor's web server (temps); deploys a copy to
           %LOCALAPPDATA% and registers a Scheduled Task at logon.

Only the Python standard library is used here — the venv (psutil, pyyaml) is
created by this script.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SYSTEM = platform.system()
LABEL = "com.homelab.metricagent"
TASK_NAME = "HomelabMetricAgent"
UNIT_NAME = "homelab-metric-agent"
# launchd / Task Scheduler run with a minimal PATH — make sure Homebrew is on it.
PATH_ENV = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


def log(msg: str) -> None:
    print(f"[bootstrap] {msg}")


def is_admin() -> bool:
    """True if this process is elevated (Windows) / running as root (POSIX)."""
    if SYSTEM == "Windows":
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    return os.geteuid() == 0


def run(cmd, check=False):
    log("$ " + " ".join(str(c) for c in cmd))
    return subprocess.run([str(c) for c in cmd], check=check)


def pick_config(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.is_file():
            sys.exit(f"config not found: {p}")
        return p
    for name in ("config.local.yaml", "config.yaml"):
        if (ROOT / name).is_file():
            return ROOT / name
    sys.exit("no config.yaml next to bootstrap.py")


def ensure_venv(venv_dir: Path) -> Path:
    py = venv_dir / ("Scripts/python.exe" if SYSTEM == "Windows" else "bin/python3")
    if not py.exists():
        base = shutil.which("python3") or shutil.which("python") or sys.executable
        run([base, "-m", "venv", venv_dir], check=True)
    reqs = ROOT / "requirements.txt"
    target = ["-r", str(reqs)] if reqs.is_file() else ["psutil", "pyyaml"]
    run([py, "-m", "pip", "install", "-q", *target], check=True)
    return py


def deploy(dest: Path, config: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    for f in ("agent.py", "requirements.txt"):
        shutil.copy2(ROOT / f, dest / f)
    shutil.copy2(config, dest / "config.yaml")
    return dest / "config.yaml"


def exec_agent(py: Path, agent: Path, config: Path):
    log("running in the foreground — Ctrl-C to stop")
    os.execv(str(py), [str(py), str(agent), "-c", str(config)])


# --------------------------------------------------------------------------- macOS


def setup_macos(args, config):
    plist = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
    if args.uninstall:
        run(["launchctl", "unload", plist])
        plist.unlink(missing_ok=True)
        log("removed launchd agent")
        return

    if platform.machine() == "arm64" and not shutil.which("macmon"):
        if shutil.which("brew"):
            log("installing macmon for CPU/GPU temperatures…")
            run(["brew", "install", "macmon"])
        else:
            log("WARNING: macmon missing and Homebrew not found — temps will be "
                "skipped. `brew install macmon` and re-run to enable them.")

    app = Path.home() / "Library/Application Support/homelab-metric-agent"
    dep_cfg = deploy(app, config)
    py = ensure_venv(app / ".venv")

    if args.foreground:
        exec_agent(py, app / "agent.py", dep_cfg)

    logf = Path.home() / "Library/Logs/homelab-metric-agent.log"
    logf.parent.mkdir(parents=True, exist_ok=True)
    plist.parent.mkdir(parents=True, exist_ok=True)
    plist.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{py}</string>
        <string>{app / 'agent.py'}</string>
        <string>-c</string>
        <string>{dep_cfg}</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key><string>{PATH_ENV}</string>
        <key>PYTHONUNBUFFERED</key><string>1</string>
    </dict>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>ProcessType</key><string>Background</string>
    <key>StandardOutPath</key><string>{logf}</string>
    <key>StandardErrorPath</key><string>{logf}</string>
</dict>
</plist>
""")
    run(["launchctl", "unload", plist])
    run(["launchctl", "load", "-w", plist], check=True)
    log(f"launchd agent '{LABEL}' loaded — starts at login. Logs: {logf}")


# --------------------------------------------------------------------------- Linux


def setup_linux(args, config):
    unit = Path.home() / ".config/systemd/user" / f"{UNIT_NAME}.service"
    if args.uninstall:
        run(["systemctl", "--user", "disable", "--now", UNIT_NAME])
        unit.unlink(missing_ok=True)
        run(["systemctl", "--user", "daemon-reload"])
        log("removed systemd --user service")
        return

    procver = Path("/proc/version")
    if procver.is_file() and "microsoft" in procver.read_text().lower():
        log("WARNING: running under WSL — host temperature / disk / network are "
            "not visible from here. Run bootstrap.py natively on Windows instead.")
    elif not any(Path("/sys/class/hwmon").glob("*")):
        log("NOTE: no /sys/class/hwmon sensors — temperatures may be unavailable.")

    py = ensure_venv(ROOT / ".venv")
    if args.foreground:
        exec_agent(py, ROOT / "agent.py", config)

    if not shutil.which("systemctl"):
        sys.exit("systemctl not found. Use `python3 bootstrap.py --foreground` "
                 "or wire up your own supervisor.")

    unit.parent.mkdir(parents=True, exist_ok=True)
    unit.write_text(f"""[Unit]
Description=Homelab Metric Agent
After=network-online.target

[Service]
ExecStart={py} {ROOT / 'agent.py'} -c {config}
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
""")
    run(["systemctl", "--user", "daemon-reload"], check=True)
    run(["systemctl", "--user", "enable", "--now", UNIT_NAME], check=True)
    log(f"systemd --user service '{UNIT_NAME}' enabled and started.")
    log(f"tip: `sudo loginctl enable-linger {os.environ.get('USER', '$USER')}` "
        "to keep it running with no active login session.")


# --------------------------------------------------------------------------- Windows


RUN_KEY = r"HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"


def _win_start_now(runner: Path, agent: Path, cfg: Path) -> None:
    """Launch the agent detached so it survives this shell exiting."""
    DETACHED_PROCESS = 0x00000008
    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen(
        [str(runner), str(agent), "-c", str(cfg)],
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
        close_fds=True,
    )
    log("agent started in the background.")


def _win_install_run_key(cmdline: str) -> bool:
    """Per-user logon autostart via HKCU Run — needs no elevation and no Task
    Scheduler access. Returns True on success."""
    ps = (
        f"$ErrorActionPreference = 'Stop'; "
        f"Set-ItemProperty -Path '{RUN_KEY}' -Name '{TASK_NAME}' -Value '{cmdline}'"
    )
    try:
        run(["powershell.exe", "-NoProfile", "-Command", ps], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def setup_windows(args, config):
    if args.uninstall:
        run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
        run(["powershell.exe", "-NoProfile", "-Command",
             f"Remove-ItemProperty -Path '{RUN_KEY}' -Name '{TASK_NAME}' "
             f"-ErrorAction SilentlyContinue"])
        run(["powershell.exe", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name = 'pythonw.exe'\" "
             "| Where-Object CommandLine -like '*homelab-metric-agent*' "
             "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"])
        log("removed scheduled task + Run-key autostart; stopped the running agent")
        return

    try:
        urllib.request.urlopen("http://localhost:8085/data.json", timeout=3).read(1)
        log("LibreHardwareMonitor web server reachable — temps enabled.")
    except (urllib.error.URLError, OSError):
        log("WARNING: LibreHardwareMonitor not reachable at "
            "http://localhost:8085/data.json — temperatures will be skipped.")
        log("  Install: https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases")
        log("  then Options > Remote Web Server (port 8085) > Run, + Run On Windows Startup.")

    app = Path(os.environ["LOCALAPPDATA"]) / "homelab-metric-agent"
    dep_cfg = deploy(app, config)
    py = ensure_venv(app / ".venv")

    if args.foreground:
        exec_agent(py, app / "agent.py", dep_cfg)

    pyw = app / ".venv/Scripts/pythonw.exe"
    runner = pyw if pyw.exists() else py

    # The agent only needs psutil + an HTTP read of LibreHardwareMonitor, so it
    # runs fine as a normal user. Register a per-user logon task at the "Limited"
    # run level — that needs no elevation. `-RunLevel Highest` here is what makes
    # Register-ScheduledTask fail with "Access is denied" from a non-elevated
    # shell; only ask for it when we are already elevated.
    run_level = "Highest" if is_admin() else "Limited"
    ps = (
        f"$ErrorActionPreference = 'Stop'; "
        f"$a = New-ScheduledTaskAction -Execute '{runner}' "
        f"-Argument '\"{app / 'agent.py'}\" -c \"{dep_cfg}\"'; "
        f"$t = New-ScheduledTaskTrigger -AtLogOn; "
        f"$p = New-ScheduledTaskPrincipal -UserId $env:USERNAME "
        f"-LogonType Interactive -RunLevel {run_level}; "
        f"$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries "
        f"-DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) "
        f"-RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1); "
        f"Register-ScheduledTask -TaskName '{TASK_NAME}' -Action $a -Trigger $t "
        f"-Principal $p -Settings $s -Force"
    )
    agent = app / "agent.py"
    cmdline = f'"{runner}" "{agent}" -c "{dep_cfg}"'

    try:
        run(["powershell.exe", "-NoProfile", "-Command", ps], check=True)
        run(["schtasks", "/Run", "/TN", TASK_NAME])
        log(f"scheduled task '{TASK_NAME}' registered (runs at logon, run level "
            f"{run_level}) and started.")
        return
    except subprocess.CalledProcessError:
        log("could not register a Scheduled Task (likely blocked by policy on a "
            "managed PC) — falling back to a per-user Run-key autostart.")

    if _win_install_run_key(cmdline):
        log(f"autostart installed: HKCU\\...\\Run\\{TASK_NAME} (starts at next logon).")
        _win_start_now(runner, agent, dep_cfg)
        return

    log("ERROR: both autostart methods failed.")
    log("  Run the agent yourself, or add this to a shortcut in shell:startup —")
    log(f"  {cmdline}")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="Bootstrap the homelab metric agent")
    ap.add_argument("--config", help="path to a config file (default: config.local.yaml then config.yaml)")
    ap.add_argument("--foreground", action="store_true", help="run now instead of installing a service")
    ap.add_argument("--uninstall", action="store_true", help="stop and remove the autostart service")
    args = ap.parse_args()

    config = None if args.uninstall else pick_config(args.config)
    if config:
        log(f"platform={SYSTEM}  config={config}")

    dispatch = {"Darwin": setup_macos, "Linux": setup_linux, "Windows": setup_windows}
    fn = dispatch.get(SYSTEM)
    if not fn:
        sys.exit(f"unsupported platform: {SYSTEM}")
    fn(args, config)


if __name__ == "__main__":
    main()
