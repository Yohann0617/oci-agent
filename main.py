import psutil
import platform
import requests
import json
import time


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


# 获取系统信息的函数
def get_system_info():
    up, down = get_network_speed()
    # 获取操作系统信息
    system_info = {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.architecture(),
        "cpu_count": psutil.cpu_count(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent
        },
        "disk": {
            "total": psutil.disk_usage('/').total,
            "used": psutil.disk_usage('/').used,
            "free": psutil.disk_usage('/').free,
            "percent": psutil.disk_usage('/').percent
        },
        "network": {
            "bytes_sent": psutil.net_io_counters().bytes_sent,
            "bytes_recv": psutil.net_io_counters().bytes_recv,
            "up": up,
            "down": down,
        }
    }
    return system_info


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
    server_url = "http://your-java-server-url/heartbeat"
    while True:
        # 上报系统信息
        system_info = get_system_info()
        report_to_server(system_info, "http://your-java-server-url/report")

        # 发送心跳
        send_heartbeat(server_url)

        time.sleep(60)  # 每分钟上报一次信息


if __name__ == "__main__":
    # main()

    json_str = json.dumps(get_system_info())
    print(json_str)

    # while True:
    #     up, down = get_network_speed()
    #     print(f"Upload: {up:.2f} B/s, Download: {down:.2f} B/s")
