import filecmp
import json
import shutil
from datetime import datetime

def backup_path(source_path, destination_dir):
    source_path = source_path.resolve()
    destination_dir = destination_dir.resolve()

    if not source_path.is_file() and not source_path.is_dir():
        raise ValueError(
            f"源路径不存在，或不是普通文件/目录：{source_path}"
        )

    if source_path.is_dir():
        if (
            destination_dir == source_path
            or source_path in destination_dir.parents
        ):
            raise ValueError(
                "备份目标目录不能等于源目录，也不能位于源目录内部"
            )

    destination_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_dir = destination_dir / f"backup_{timestamp}"
    backup_dir.mkdir()

    target_path = backup_dir / source_path.name

    if source_path.is_file():
        shutil.copy2(source_path, target_path)

        if not filecmp.cmp(source_path, target_path, shallow=False):
            raise OSError("备份文件内容校验失败")
    else:
        shutil.copytree(
            source_path,
            target_path,
            symlinks=True
        )

    return target_path

def save_backup_record(source_path, target_path):
    # 忽略大小写比较，兼容 Windows 常见的文件名匹配方式。
    record_name = "backup_record.json"
    if target_path.name.casefold() == record_name:
        record_name = "backup_record_meta.json"
    record_path = target_path.parent / record_name

    record = {
        "recorded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_path": str(source_path.resolve()),
        "target_path": str(target_path.resolve()),
        "source_type": "directory" if target_path.is_dir() else "file",
        "status": "completed"
    }

    with open(record_path, "x", encoding="utf-8") as record_file:
        json.dump(
            record,
            record_file,
            ensure_ascii=False,
            indent=4
        )
        record_file.write("\n")

    return record_path
