import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from backup_ops import backup_path, save_backup_record
from log_ops import analyze_log, save_analysis_report
from inspection_ops import get_server_info, check_server, save_report

BASE_DIR = Path(__file__).resolve().parent
SERVICE_FILE = BASE_DIR / "service.list"
LOG_FILE = BASE_DIR / "inspection.log"
REPORT_DIR = BASE_DIR / "reports"
CONFIG_FILE = BASE_DIR / "config.json"

def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as config_file:
            config = json.load(config_file)

        if not isinstance(config, dict):
            raise ValueError("配置文件最外层必须是 JSON 对象")

        thresholds = config.get("thresholds")

        if not isinstance(thresholds, dict):
            raise ValueError("配置中必须包含 thresholds 对象")

        for name in ["cpu", "memory", "disk"]:
            value = thresholds.get(name)

            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(
                    f"thresholds.{name} 必须存在，并且是数字"
                )

            if not 0 <= value <= 100:
                raise ValueError(
                    f"thresholds.{name} 必须在 0 到 100 之间"
                )

        log_analysis = config.get("log_analysis")

        if not isinstance(log_analysis, dict):
            raise ValueError("配置中必须包含 log_analysis 对象")

        log_path = log_analysis.get("path")

        if not isinstance(log_path, str) or log_path.strip() == "":
            raise ValueError(
                "log_analysis.path 必须是非空字符串"
            )

        backup_config = config.get("backup")

        if not isinstance(backup_config, dict):
            raise ValueError("配置中必须包含 backup 对象")

        for name in ["source", "destination"]:
            value = backup_config.get(name)

            if not isinstance(value, str) or value.strip() == "":
                raise ValueError(
                    f"backup.{name} 必须是非空字符串"
                )

        return config
    except (OSError, ValueError) as error:
        print(f"配置读取失败：{CONFIG_FILE}")
        print(f"原因：{error}")
        sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser(
        description="服务器自动化运维工具集"
    )

    parser.add_argument(
        "--no-service",
        action="store_true",
        help="跳过 Linux 服务状态检查"
    )

    parser.add_argument(
        "--process-sort",
        choices=["cpu", "memory"],
        default="cpu",
        help="进程排序依据：cpu 或 memory，默认 cpu"
    )

    mode_group = parser.add_mutually_exclusive_group()

    mode_group.add_argument(
        "--analyze-log",
        nargs="?",
        const="",
        default=None,
        help="分析日志；省略路径时使用 config.json 中的配置"
    )

    mode_group.add_argument(
        "--backup",
        action="store_true",
        help="按 config.json 中的配置备份文件或目录"
    )

    return parser.parse_args()

def main():
    args = parse_args()

    if args.backup:
        config = load_config()

        source_path = Path(config["backup"]["source"])
        destination_dir = Path(config["backup"]["destination"])

        if not source_path.is_absolute():
            source_path = BASE_DIR / source_path

        if not destination_dir.is_absolute():
            destination_dir = BASE_DIR / destination_dir

        try:
            target_path = backup_path(source_path, destination_dir)
        except (OSError, ValueError) as error:
            print(f"备份失败：{error}")
            sys.exit(1)

        print(f"备份源：{source_path}")
        print(f"备份位置：{target_path}")
        print("备份完成")

        try:
            record_path = save_backup_record(source_path, target_path)
        except OSError as error:
            print(f"备份内容已保存，但备份记录写入失败：{error}")
            sys.exit(1)

        print(f"备份记录：{record_path}")

        return

    if args.analyze_log is not None:
        if args.analyze_log == "":
            config = load_config()
            log_path = Path(config["log_analysis"]["path"])
        else:
            log_path = Path(args.analyze_log)

        if not log_path.is_absolute():
            log_path = BASE_DIR / log_path

        analysis = analyze_log(log_path)

        if analysis["error"] != "":
            print(f"日志分析失败：{analysis['error']}")
            sys.exit(1)

        print(f"分析文件：{log_path}")
        print(f"总行数：{analysis['total_lines']}")
        print(f"ERROR 行数：{analysis['error_lines']}")
        print(f"WARNING 行数：{analysis['warning_lines']}")

        if len(analysis["matches"]) == 0:
            print("未发现匹配的关键字")
        else:
            print("匹配内容（最多展示前 20 条）：")

            for match in analysis["matches"]:
                print(
                    f"第 {match['line_number']} 行："
                    f"{match['text']}"
                )

        try:
            report_path = save_analysis_report(
                log_path,
                analysis,
                report_dir=REPORT_DIR
            )
        except OSError as error:
            print(f"报告保存失败：{error}")
            sys.exit(1)

        print(f"分析报告已保存：{report_path}")

        return

    config = load_config()
    thresholds = config["thresholds"]

    servers = [
        get_server_info(
            service_file_path=SERVICE_FILE,
            check_services=not args.no_service,
            process_sort=args.process_sort
        )
    ]
    check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("服务器自动化运维工具集（跨平台版）")
    print("================================")
    print("开始服务器巡检")
    print(f"巡检时间：{check_time}")

    for server in servers:
        print()
        print(f"服务器名称：{server['name']}")
        print(f"操作系统：{server['system']}")
        print(f"CPU 使用率：{server['cpu']}%")
        print(f"内存使用率：{server['memory']}%")
        print(f"磁盘 {server['disk_path']} 使用率：{server['disk']}%")

        if len(server["network"]) > 0:
            print("网络累计流量：")

            for interface_name, network_data in server["network"].items():
                print(
                    f"- {interface_name}："
                    f"发送 {network_data['sent_mib']:.2f} MiB，"
                    f"接收 {network_data['recv_mib']:.2f} MiB"
                )
        else:
            print("网络统计：未获取到网卡数据")

        if server["service_check_enabled"]:
            print("服务状态：")

            for service_name, service_status in server["services"].items():
                print(f"- {service_name}:{service_status}")
        else:
            print("服务检查：已跳过")
        process_info = server["processes"]

        if not process_info["supported"]:
            print("进程查询：当前版本仅支持 Linux")
        elif process_info["error"] != "":
            print(f"进程查询失败：{process_info['error']}")
        else:
            print(
                f"{process_info['sort_label']} "
                f"占用前五的进程（ps 统计口径）："
            )
            print("    PID  CPU% MEM% 进程名称")

            for row in process_info["rows"]:
                print(row)
        result = check_server(server, thresholds)

        if len(result) == 0:
            print("巡检状态：正常")
        else:
            print("巡检状态：异常")
            print("告警信息：")

            for alert in result:
                print(f"- {alert}")

        try:
            save_report(
                server,
                result,
                check_time,
                log_path=LOG_FILE
            )
        except OSError as error:
            print(f"巡检日志保存失败：{LOG_FILE}")
            print(f"原因：{error}")
            sys.exit(1)

    print("================================")
    print("服务器巡检完成")

if __name__ == "__main__":
    main()