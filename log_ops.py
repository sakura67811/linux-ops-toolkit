import json
from datetime import datetime

def analyze_log(log_path):
    analysis = {
        "total_lines": 0,
        "error_lines": 0,
        "warning_lines": 0,
        "matches": [],
        "error": ""
    }

    try:
        with open(log_path, "r", encoding="utf-8") as log_file:
            for line_number, line in enumerate(log_file, start=1):
                analysis["total_lines"] += 1

                upper_line = line.upper()

                has_error = "ERROR" in upper_line
                has_warning = "WARNING" in upper_line

                if has_error:
                    analysis["error_lines"] += 1

                if has_warning:
                    analysis["warning_lines"] += 1

                if has_error or has_warning:
                    if len(analysis["matches"]) < 20:
                        analysis["matches"].append({
                            "line_number": line_number,
                            "text": line.strip()
                        })

    except OSError as error:
        analysis["error"] = f"无法读取日志：{error}"

    except UnicodeError:
        analysis["error"] = "日志不是有效的 UTF-8 文本"

    return analysis

def save_analysis_report(log_path, analysis, report_dir):
    report_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
    report_path = report_dir / f"log_analysis_{timestamp}.json"

    report_data = {
        "source_file": str(log_path),
        "analyzed_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "total_lines": analysis["total_lines"],
        "error_lines": analysis["error_lines"],
        "warning_lines": analysis["warning_lines"],
        "matches": analysis["matches"]
    }

    with open(report_path, "x", encoding="utf-8") as report_file:
        json.dump(
            report_data,
            report_file,
            ensure_ascii=False,
            indent=4
        )
        report_file.write("\n")

    return report_path