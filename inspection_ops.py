import platform
import subprocess
import sys

import psutil

COMMAND_TIMEOUT = 5

def load_services(service_file_path):
    services = []

    try:
        with open(
            service_file_path,
            "r",
            encoding="utf-8"
        ) as service_file:
            for line in service_file:
                service = line.strip()

                if service != "" and not service.startswith("#"):
                    services.append(service)

    except (OSError, UnicodeError) as error:
        print(f"服务配置读取失败：{service_file_path}")
        print(f"原因：{error}")
        sys.exit(1)

    if len(services) == 0:
        print(f"配置错误：服务配置文件为空：{service_file_path}")
        sys.exit(1)

    return services

def get_service_status(services):
    service_status = {}

    for service in services:
        try:
            load_result = subprocess.run(
                [
                    "systemctl",
                    "show",
                    "--property=LoadState",
                    "--value",
                    service
                ],
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT
            )

            load_state = load_result.stdout.strip()

            if load_state == "loaded":
                active_result = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True,
                    timeout=COMMAND_TIMEOUT
                )

                status = active_result.stdout.strip()

                if status == "":
                    status = "check-error"
            else:
                if load_state == "":
                    status = "check-error"
                else:
                    status = load_state

        except FileNotFoundError:
            status = "command-not-found"

        except OSError:
            status = "check-error"

        service_status[service] = status

    return service_status

def get_network_info():
    network_info = {}

    counters = psutil.net_io_counters(pernic=True)

    for interface_name, counter in counters.items():
        network_info[interface_name] = {
            "sent_mib": round(counter.bytes_sent / 1024 / 1024, 2),
            "recv_mib": round(counter.bytes_recv / 1024 / 1024, 2)
        }

    return network_info

def get_top_processes(limit=5, sort_by="cpu"):
    sort_fields = {
        "cpu": "pcpu",
        "memory": "pmem"
    }

    sort_labels = {
        "cpu": "CPU",
        "memory": "内存"
    }

    process_info = {
        "supported": False,
        "rows": [],
        "error": "",
        "sort_label": sort_labels[sort_by]
    }

    if platform.system() != "Linux":
        return process_info

    process_info["supported"] = True

    try:
        result = subprocess.run(
            [
                "ps",
                "-eo",
                "pid,pcpu,pmem,comm",
                f"--sort=-{sort_fields[sort_by]}",
                "--no-headers"
            ],
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
            check=True
        )

        lines = result.stdout.splitlines()
        process_info["rows"] = lines[:limit]

        if len(process_info["rows"]) == 0:
            process_info["error"] = "ps 未返回进程信息"

    except subprocess.TimeoutExpired:
        process_info["error"] = "进程查询超时"

    except subprocess.CalledProcessError as error:
        process_info["error"] = (
            f"ps 查询失败，返回码：{error.returncode}"
        )

    except OSError as error:
        process_info["error"] = f"无法执行 ps：{error}"

    return process_info

def get_server_info(
    service_file_path,
    check_services=True,
    process_sort="cpu"
):
    system_name = platform.system()

    if system_name == "Windows":
        disk_path = "C:/"
    elif system_name == "Linux":
        disk_path = "/"
    else:
        disk_path = "/"
    service_check_enabled = system_name == "Linux" and check_services
    if service_check_enabled:
        service_names = load_services(service_file_path)
        services = get_service_status(service_names)
    else:
        services = {}

    server_info = {
        "name": platform.node(),
        "system": system_name,
        "disk_path": disk_path,
        "service_check_enabled":service_check_enabled,
        "services": services,
        "network": get_network_info(),
        "processes": get_top_processes(sort_by=process_sort),
        "cpu": psutil.cpu_percent(interval=1),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage(disk_path).percent
    }

    return server_info

def check_server(server, thresholds):
    alerts = []
    if server["cpu"] > thresholds["cpu"]:
        alerts.append(f"CPU 使用率过高: {server['cpu']}%")
    if server["memory"] > thresholds["memory"]:
        alerts.append(f"内存使用率过高: {server['memory']}%")
    if server["disk"] > thresholds["disk"]:
        alerts.append(f"磁盘使用率过高:{server['disk']}%")
    for service_name, service_status in server["services"].items():
        if service_status == "check-timeout":
            alerts.append(
                f"服务 {service_name} 查询超时，无法确定状态"
            )
        elif service_status == "command-not-found":
            alerts.append(
                f"服务 {service_name} 检查失败：找不到 systemctl 命令"
            )
        elif service_status == "check-error":
            alerts.append(
                f"服务 {service_name} 查询失败，无法确定状态"
            )
        elif service_status == "not-found":
            alerts.append(
                f"服务 {service_name} 对应的服务单元不存在"
            )
        elif service_status == "failed":
            alerts.append(
                f"服务 {service_name} 处于失败状态"
            )
        elif service_status == "masked":
            alerts.append(
                f"服务 {service_name} 已被屏蔽"
            )
        elif service_status != "active":
            alerts.append(
                f"服务 {service_name} 未处于 active 状态：{service_status}"
            )

    if server["processes"]["error"] != "":
        alerts.append(
            f"进程检查失败：{server['processes']['error']}"
        )

    return alerts

def save_report(server, result, check_time, log_path):
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{check_time}] ")
        log_file.write(f"服务器:{server['name']} | ")
        log_file.write(f"系统:{server['system']} | ")
        log_file.write(f"CPU:{server['cpu']}% | ")
        log_file.write(f"内存:{server['memory']}% | ")
        log_file.write(f"磁盘({server['disk_path']}):{server['disk']}% | ")

        if len(server["network"]) > 0:
            for interface_name, network_data in server["network"].items():
                log_file.write(
                    f"网卡 {interface_name}："
                    f"累计发送 {network_data['sent_mib']:.2f} MiB，"
                    f"累计接收 {network_data['recv_mib']:.2f} MiB | "
                )
        else:
            log_file.write("网络统计：未获取到网卡数据 | ")

        if server["service_check_enabled"]:
            service_records = []

            for service_name, service_status in server["services"].items():
                service_records.append(
                f"{service_name}={service_status}"
                )

            service_text = "; ".join(service_records)
            log_file.write(f"服务：{service_text} | ")
        else:
            log_file.write("服务检查：已跳过 | ")

        # 新增：保存进程查询结果
        process_info = server["processes"]

        if not process_info["supported"]:
            log_file.write("进程查询：当前版本仅支持 Linux | ")
        elif process_info["error"] != "":
            log_file.write(
                f"进程查询失败：{process_info['error']} | "
            )
        else:
            process_text = "; ".join(process_info["rows"])

            log_file.write(
                f"{process_info['sort_label']}进程前五"
                f"（PID CPU% MEM% 名称）："
                f"{process_text} | "
            )

        # 原有：保存最终巡检状态和告警
        if len(result) == 0:
            log_file.write("状态：正常\n")
        else:
            alert_text = ";".join(result)
            log_file.write(f"状态：异常 | 告警：{alert_text}\n")