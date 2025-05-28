import socket
import psutil
import platform
import requests
import json
import time
import os
import subprocess
from datetime import datetime


# ---------- 辅助函数 ----------

def format_bytes(size):
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.2f}{units[i]}" if size != int(size) else f"{int(size)}{units[i]}"


def format_uptime(uptime_timedelta):
    days = uptime_timedelta.days
    if days >= 1:
        return f"{days}天"
    else:
        total_seconds = int(uptime_timedelta.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:02}"


# ---------- 获取信息 ----------

def get_cpu_model():
    system = platform.system()
    try:
        if system in ("Linux", "FreeBSD"):
            # 尝试从 lscpu 获取
            try:
                output = subprocess.check_output(["lscpu"], text=True)
                for line in output.splitlines():
                    if "Model name" in line:
                        return line.split(":", 1)[1].strip()
                    if "Architecture" in line and "ARM" in line:
                        return platform.processor() or "ARM CPU"
            except Exception:
                pass

            # 尝试从 /proc/cpuinfo 获取 ARM 信息
            with open("/proc/cpuinfo") as f:
                lines = f.readlines()

            implementer = part = None
            for line in lines:
                if "CPU implementer" in line:
                    implementer = line.strip().split(":")[1].strip()
                elif "CPU part" in line:
                    part = line.strip().split(":")[1].strip()

            if implementer and part:
                return f"ARM CPU (implementer: {implementer}, part: {part})"

        elif system == "Darwin":
            return subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
        elif system == "Windows":
            cmd = ['powershell', '-Command', "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name"]
            return subprocess.check_output(cmd, encoding="utf-8").strip()
    except Exception as e:
        return f"Unknown ({e})"
    return "Unknown"


def get_load_average():
    if platform.system() in ("Linux", "Darwin", "FreeBSD"):
        try:
            one, five, fifteen = os.getloadavg()
            return {
                "1min": round(one, 2),
                "5min": round(five, 2),
                "15min": round(fifteen, 2)
            }
        except Exception as e:
            return {"note": f"Load average error: {e}"}
    return {"note": "Not supported on Windows"}


def get_disk_usage():
    total, used, free = 0, 0, 0
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            total += usage.total
            used += usage.used
            free += usage.free
        except PermissionError:
            continue
    percent = (used / total * 100) if total > 0 else 0
    return {
        "total": format_bytes(total),
        "used": format_bytes(used),
        "percent": round(percent, 1)
    }


def get_network_speed(interval=1):
    net1 = psutil.net_io_counters()
    time.sleep(interval)
    net2 = psutil.net_io_counters()
    upload = (net2.bytes_sent - net1.bytes_sent) / interval
    download = (net2.bytes_recv - net1.bytes_recv) / interval
    return upload, download


def get_virtualization_type():
    if platform.system() != "Linux":
        return "Unknown"
    try:
        if os.path.exists("/proc/1/environ"):
            with open("/proc/1/environ", 'rb') as f:
                env = f.read()
            if b'lxc' in env or b'container=lxc' in env:
                return "LXC"
            if b'docker' in env or b'container=docker' in env:
                return "Docker"

        result = subprocess.run(["systemd-detect-virt"], capture_output=True, text=True)
        if result.returncode == 0:
            output = result.stdout.strip()
            if output != "none":
                return output.upper()

        with open("/proc/cpuinfo") as f:
            cpuinfo = f.read().lower()
            if "kvm" in cpuinfo:
                return "KVM"
            elif "vmware" in cpuinfo:
                return "VMware"
            elif "xen" in cpuinfo:
                return "Xen"
    except:
        pass
    return "Physical"


def get_os_version():
    system = platform.system()
    try:
        if system == "Linux":
            # Alpine
            if os.path.exists("/etc/alpine-release"):
                with open("/etc/alpine-release") as f:
                    return f"alpine-{f.read().strip()}"

            # Debian
            if os.path.exists("/etc/debian_version"):
                with open("/etc/debian_version") as f:
                    version = f.read().strip()
                    return f"debian-{version}"

            # CentOS / RHEL / Rocky / AlmaLinux
            if os.path.exists("/etc/redhat-release"):
                with open("/etc/redhat-release") as f:
                    line = f.read().strip().lower()
                    parts = line.split()
                    if len(parts) >= 4:
                        name = parts[0]
                        version = parts[3]
                        return f"{name.replace('linux', '').strip()}-{version}"

            # Ubuntu / Linux Mint
            if os.path.exists("/etc/lsb-release"):
                distro = ""
                version = ""
                with open("/etc/lsb-release") as f:
                    for line in f:
                        if line.startswith("DISTRIB_ID="):
                            distro = line.strip().split("=")[1].lower()
                        if line.startswith("DISTRIB_RELEASE="):
                            version = line.strip().split("=")[1]
                    if distro and version:
                        return f"{distro}-{version}"

            # 通用 fallback：/etc/os-release
            if os.path.exists("/etc/os-release"):
                info = {}
                with open("/etc/os-release") as f:
                    for line in f:
                        if "=" in line:
                            key, value = line.strip().split("=", 1)
                            info[key] = value.strip('"')
                os_id = info.get("ID", "")
                version = info.get("VERSION_ID", "")
                if os_id and version:
                    return f"{os_id}-{version}"
                elif "PRETTY_NAME" in info:
                    return info["PRETTY_NAME"]

        elif system == "Darwin":
            return f"macos-{subprocess.check_output(['sw_vers', '-productVersion'], text=True).strip()}"

        elif system == "Windows":
            return f"windows-{platform.platform()}"

        elif system == "FreeBSD":
            return f"freebsd-{subprocess.check_output(['freebsd-version'], text=True).strip()}"

    except Exception as e:
        return f"Unknown ({e})"

    return "Unknown"


# ---------- 主函数 ----------

def get_system_info():
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    now = datetime.now()
    uptime = now - boot_time
    upload, download = get_network_speed()

    return {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "distribution": get_os_version(),
        "virtualization": get_virtualization_type(),
        "architecture": platform.machine(),
        "cpu": {
            "model": get_cpu_model(),
            "count": psutil.cpu_count(logical=True),
            "percent": psutil.cpu_percent(interval=1)
        },
        "memory": {
            "total": format_bytes(psutil.virtual_memory().total),
            "used": format_bytes(psutil.virtual_memory().used),
            "percent": psutil.virtual_memory().percent
        },
        "disk": get_disk_usage(),
        "network": {
            "upload_speed": format_bytes(upload),
            "download_speed": format_bytes(download)
        },
        "load_average": get_load_average(),
        "uptime": format_uptime(uptime),
        "boot_time": boot_time.strftime('%Y-%m-%d %H:%M:%S'),
        "current_time": now.strftime('%Y-%m-%d %H:%M:%S'),
        "process_count": len(psutil.pids()),
        "connection_count": {
            "tcp": sum(1 for c in psutil.net_connections() if c.type == socket.SOCK_STREAM),
            "udp": sum(1 for c in psutil.net_connections() if c.type == socket.SOCK_DGRAM),
        }
    }


# 上报数据到Java服务端
def report_to_server(data, url):
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, data=json.dumps(data), headers=headers)
        if response.status_code == 200:
            print("Successfully reported to server.")
        else:
            print(f"Failed to report, server returned status code {response.status_code}")
    except Exception as e:
        print(f"Error reporting to server: {e}")


# 心跳机制
def send_heartbeat(url):
    heartbeat = {
        "status": "online",
        "timestamp": time.time()
    }
    report_to_server(heartbeat, url)


# 主函数
def main():
    while True:
        # 上报系统信息
        system_info = get_system_info()
        report_to_server(system_info, "http://your-java-server-url/report")

        # 发送心跳
        send_heartbeat("http://your-java-server-url/heartbeat")

        time.sleep(60)  # 每分钟上报一次信息


if __name__ == "__main__":
    # main()

    json_str = json.dumps(get_system_info())
    print(json_str)

    while True:
        up, down = get_network_speed()
        print(f"Upload: {format_bytes(up)}, Download: {format_bytes(down)}")
