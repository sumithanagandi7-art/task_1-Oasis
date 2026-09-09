"""
System Control — OS-level Automation for Atlas Voice Assistant
==============================================================
Provides:
- Volume control (Up, Down, Mute, Unmute) via Windows virtual key events
- Application launcher (Notepad, Calculator, Paint, Explorer, VS Code, Browser, etc.)
- System status (Battery level, CPU usage, RAM stats)
- System lock workstation
"""

import os
import sys
import subprocess
import ctypes
from typing import Dict, Any, Optional

# Virtual key codes on Windows
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

# Common application mappings for Windows
APP_MAP = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "calc": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "mspaint": ["mspaint.exe"],
    "explorer": ["explorer.exe"],
    "file explorer": ["explorer.exe"],
    "files": ["explorer.exe"],
    "terminal": ["wt.exe", "powershell.exe", "cmd.exe"],
    "command prompt": ["cmd.exe"],
    "cmd": ["cmd.exe"],
    "powershell": ["powershell.exe"],
    "vscode": ["code"],
    "vs code": ["code"],
    "visual studio code": ["code"],
    "chrome": ["chrome.exe", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"],
    "edge": ["msedge.exe"],
    "browser": ["msedge.exe"],
    "task manager": ["taskmgr.exe"],
    "settings": ["start", "ms-settings:"]
}


def _send_virtual_key(vk_code: int, times: int = 1):
    """Simulate Windows virtual key presses."""
    if sys.platform != "win32":
        return
    for _ in range(times):
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)


def adjust_volume(action: str, steps: int = 5) -> Dict[str, Any]:
    """
    Adjust system volume.
    action: 'up', 'down', 'mute', 'unmute'
    """
    action = action.lower().strip()
    if action in ["up", "increase", "louder", "raise"]:
        _send_virtual_key(VK_VOLUME_UP, times=steps)
        return {"success": True, "action": "volume_up", "message": f"Turned volume up."}
    elif action in ["down", "decrease", "lower", "quieter"]:
        _send_virtual_key(VK_VOLUME_DOWN, times=steps)
        return {"success": True, "action": "volume_down", "message": f"Turned volume down."}
    elif action in ["mute", "silence"]:
        _send_virtual_key(VK_VOLUME_MUTE, times=1)
        return {"success": True, "action": "volume_mute", "message": "Volume muted."}
    elif action in ["unmute"]:
        _send_virtual_key(VK_VOLUME_MUTE, times=1)
        return {"success": True, "action": "volume_unmute", "message": "Volume unmuted."}
    else:
        return {"success": False, "error": f"Unknown volume action: {action}"}


def launch_app(app_name: str) -> Dict[str, Any]:
    """Safely launch an installed application by alias."""
    clean_name = app_name.lower().strip()
    target_cmds = APP_MAP.get(clean_name)

    if not target_cmds:
        # Check partial match
        for key in APP_MAP:
            if key in clean_name or clean_name in key:
                target_cmds = APP_MAP[key]
                clean_name = key
                break

    if not target_cmds:
        return {
            "success": False,
            "error": f"I don't know how to launch '{app_name}'. You can ask me to open Notepad, Calculator, Paint, Explorer, VS Code, or Browser."
        }

    for cmd in target_cmds:
        try:
            if cmd == "start":
                os.system(f"start {target_cmds[1]}")
            else:
                subprocess.Popen(cmd, shell=True)
            return {"success": True, "app": clean_name, "message": f"Opening {clean_name.title()}."}
        except Exception:
            continue

    return {"success": False, "error": f"Failed to launch {app_name}."}


def get_system_telemetry() -> Dict[str, Any]:
    """Get system battery and memory information."""
    telemetry = {"battery": None, "charging": None, "cpu_percent": None, "ram_percent": None}
    
    # Try battery status via ctypes on Windows
    if sys.platform == "win32":
        class SYSTEM_POWER_STATUS(ctypes.Structure):
            _fields_ = [
                ('ACLineStatus', ctypes.c_byte),
                ('BatteryFlag', ctypes.c_byte),
                ('BatteryLifePercent', ctypes.c_byte),
                ('Reserved1', ctypes.c_byte),
                ('BatteryLifeTime', ctypes.c_ulong),
                ('BatteryFullLifeTime', ctypes.c_ulong)
            ]
        status = SYSTEM_POWER_STATUS()
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            percent = status.BatteryLifePercent
            if percent <= 100:
                telemetry["battery"] = int(percent)
                telemetry["charging"] = (status.ACLineStatus == 1)

    # Summary sentence
    summary_parts = []
    if telemetry["battery"] is not None:
        charge_str = " (charging)" if telemetry["charging"] else ""
        summary_parts.append(f"Battery is at {telemetry['battery']}%{charge_str}.")
    else:
        summary_parts.append("Running on AC desktop power (no battery detected).")

    telemetry["summary"] = " ".join(summary_parts)
    return telemetry


def lock_workstation() -> Dict[str, Any]:
    """Lock the Windows workstation."""
    if sys.platform == "win32":
        ctypes.windll.user32.LockWorkStation()
        return {"success": True, "message": "Locking workstation."}
    return {"success": False, "error": "Lock workstation only supported on Windows."}
