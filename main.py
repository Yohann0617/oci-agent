import socket
import psutil
import platform
import requests
import json
import time
import humanize
import os
import subprocess
from datetime import datetime

humanize.naturalsize(psutil.virtual_memory().total)


# CPU 型号
def get_cpu_model():
    system = platform.system()
    try:
        if system == "Linux":
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        return line.strip().split(":")[1].strip()
        elif system == "Windows":
            # 用 PowerShell 替代 wmic
            cmd = ['powershell', '-Command', "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name"]
            output = subprocess.check_output(cmd, encoding="utf-8")
            return output.strip()
        elif system == "Darwin":
            output = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], encoding="utf-8")
            return output.strip()
    except Exception as e:
        return f"Unknown ({e})"

    return "Unknown"


# 负载（load average）
def get_load_average():
    if platform.system() == "Windows":
        return {
            "1min": None,
            "5min": None,
            "15min": None,
            "note": "Load average not supported on Windows"
        }
    else:
        try:
            one, five, fifteen = os.getloadavg()
            return {
                "1min": round(one, 2),
                "5min": round(five, 2),
                "15min": round(fifteen, 2)
            }
        except Exception as e:
            return {
                "1min": None,
                "5min": None,
                "15min": None,
                "note": f"Error: {e}"
            }


# 启动时间 & 当前活动时间
def get_uptime_info():
    boot_timestamp = psutil.boot_time()
    boot_time = datetime.fromtimestamp(boot_timestamp)
    now = datetime.now()
    uptime_seconds = (now - boot_time).total_seconds()
    return {
        "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S"),
        "active_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "uptime_days": int(uptime_seconds // (60 * 60 * 24))
    }


# 网络连接统计（TCP/UDP 数量）
def get_connection_counts():
    connections = psutil.net_connections()
    tcp_count = sum(1 for conn in connections if conn.type == socket.SOCK_STREAM)
    udp_count = sum(1 for conn in connections if conn.type == socket.SOCK_DGRAM)
    return {
        "tcp": tcp_count,
        "udp": udp_count
    }


# 交换空间
def get_swap_info():
    swap = psutil.swap_memory()
    return {
        "total": swap.total,
        "used": swap.used,
        "percent": swap.percent
    }


# 进程数
def get_process_count():
    return len(psutil.pids())


# 获取网络收发速率
def get_network_speed(interval=1):
    # 第一次采样
    net1 = psutil.net_io_counters()
    bytes_sent1 = net1.bytes_sent
    bytes_recv1 = net1.bytes_recv

    time.sleep(interval)

    # 第二次采样
    net2 = psutil.net_io_counters()
    bytes_sent2 = net2.bytes_sent
    bytes_recv2 = net2.bytes_recv

    # 计算速率（字节每秒）
    upload_speed = (bytes_sent2 - bytes_sent1) / interval
    download_speed = (bytes_recv2 - bytes_recv1) / interval

    return upload_speed, download_speed

# 汇总所有盘的磁盘使用情况
def get_total_disk_usage():
    total = 0
    used = 0
    free = 0

    # 遍历所有分区
    partitions = psutil.disk_partitions(all=False)  # all=True会包括光驱等非实际盘符

    for part in partitions:
        try:
            usage = psutil.disk_usage(part.mountpoint)
            total += usage.total
            used += usage.used
            free += usage.free
        except PermissionError:
            # 某些系统分区可能无权限访问，跳过
            continue

    percent = (used / total * 100) if total > 0 else 0
    return {
        "total": total,
        "used": used,
        "free": free,
        "percent": round(percent, 1)
    }

# 获取系统信息总览
def get_system_info():
    up_speed, down_speed = get_network_speed()
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    now_time = datetime.now()
    uptime = now_time - boot_time
    disk = get_total_disk_usage()

    return {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "cpu": {
            "model": get_cpu_model(),
            "count": psutil.cpu_count(),
            "percent": psutil.cpu_percent(interval=1)
        },
        "memory": {
            "total": format_bytes(psutil.virtual_memory().total),
            "used": format_bytes(psutil.virtual_memory().used),
            "percent": psutil.virtual_memory().percent
        },
        "disk": {
            "total": format_bytes(disk["total"]),
            "used": format_bytes(disk["used"]),
            "percent": disk["percent"]
        },
        "network": {
            "upload_speed": format_bytes(up_speed),
            "download_speed": format_bytes(down_speed)
        },
        "load_average": get_load_average(),
        "uptime": format_uptime(uptime),
        "boot_time": boot_time.strftime('%Y-%m-%d %H:%M:%S'),
        "current_time": now_time.strftime('%Y-%m-%d %H:%M:%S'),
        "process_count": len(psutil.pids()),
        "connection_count": {
            "tcp": len([c for c in psutil.net_connections() if c.type == socket.SOCK_STREAM]),
            "udp": len([c for c in psutil.net_connections() if c.type == socket.SOCK_DGRAM]),
        }
    }


def format_bytes(size):
    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024.0
        i += 1

    if units[i] == 'B':
        return f"{int(size)}{units[i]}"
    elif size == int(size):
        return f"{int(size)}{units[i]}"
    else:
        return f"{size:.2f}{units[i]}"


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

    # while True:
    #     up, down = get_network_speed()
    #     print(f"Upload: {up:.2f} B/s, Download: {down:.2f} B/s")
