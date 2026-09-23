# 服务器自动化运维工具集

使用 Python 编写的本机运维工具，提供资源巡检、Linux 服务检查、
进程查询、日志分析，以及文件和目录备份功能。

项目曾在 Windows 和 Ubuntu 环境中进行开发与验证。
历史 Linux 开发环境使用 Python 3.12.3；收尾修订版的验收范围见文末。

## 已实现功能

- 获取主机名称、操作系统、CPU、内存和磁盘使用率。
- 按配置阈值生成资源告警。
- 显示各网卡累计发送和接收流量。
- 在 Linux 中检查 service.list 配置的 systemd 服务。
- 在 Linux 中查询 CPU 或内存占用前五的进程。
- 将巡检结果追加到 inspection.log。
- 分析 UTF-8 日志中的 ERROR、WARNING 关键字。
- 将日志分析结果保存为 JSON 报告。
- 备份单个文件或整个目录，每次生成独立的时间戳目录。
- 保存 JSON 格式的备份记录。

## 项目文件

| 文件 | 用途 |
|---|---|
| main.py | 命令入口、配置读取、执行流程和结果展示 |
| inspection_ops.py | 巡检数据采集、告警判断、巡检日志保存 |
| log_ops.py | 日志分析和分析报告保存 |
| backup_ops.py | 文件与目录备份、备份记录保存 |
| config.json | 资源阈值、默认分析路径和备份路径 |
| service.list | 需要检查的 Linux 服务名称 |
| sample.log | 日志分析样例 |
| requirements.txt | 第三方依赖及版本 |
| .gitignore | Git 忽略规则 |
| examples/ | 系统信息采集练习示例 |
| tests/ | 日志、备份及服务查询异常处理的自动化测试 |

reports、backups 和 inspection.log 在相应功能运行时生成。

## 环境准备

先在终端进入项目目录。

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Linux 需要具备创建 Python 虚拟环境所需的组件。
服务检查需要可连接 systemd 的 systemctl；进程查询依赖支持当前参数的 ps 命令。
容器或未运行 systemd 的环境可能报告服务查询失败，可以使用 --no-service 跳过。

以下命令直接使用虚拟环境里的解释器，不要求提前激活虚拟环境。

## 配置文件

config.json 示例：

```json
{
    "thresholds": {
        "cpu": 90,
        "memory": 80,
        "disk": 80
    },
    "log_analysis": {
        "path": "sample.log"
    },
    "backup": {
        "source": "backup_demo",
        "destination": "backups"
    }
}
```

- 资源使用率严格大于阈值时告警。
- 相对路径以 main.py 所在目录为基准。
- backup.source 可以指向普通文件或目录。
- 备份源必须已经存在。
- 目录备份的目标不能等于源目录，也不能位于源目录内部。

service.list 每行填写一个服务名称，支持空行和以 # 开头的注释。
请按本机实际监控需求配置。

如果配置了 mysql，而系统没有对应的服务单元，程序会报告 not-found。
这不等同于确认机器上完全没有 MySQL 软件。

## 运行命令

以下 Linux 命令在项目目录执行。

### 默认巡检

```bash
.venv/bin/python main.py
```

### 跳过服务检查

```bash
.venv/bin/python main.py --no-service
```

### 按内存占用排序查询进程

```bash
.venv/bin/python main.py --process-sort memory
```

### 分析配置中的默认日志

```bash
.venv/bin/python main.py --analyze-log
```

### 分析指定日志

```bash
.venv/bin/python main.py --analyze-log sample.log
```

### 执行备份

首次运行前，先按下文“准备备份练习目录”创建 backup_demo，
或将 backup.source 改为已经存在的文件或目录。

```bash
.venv/bin/python main.py --backup
```

### 查看命令帮助

```bash
.venv/bin/python main.py --help
```

Windows 下，将命令开头的 `.venv/bin/python` 替换为
`.\.venv\Scripts\python.exe`。例如：

```powershell
.\.venv\Scripts\python.exe main.py --analyze-log
```

--analyze-log 和 --backup 不能同时使用。

## 准备备份练习目录

示例配置使用 backup_demo，它不纳入 Git，需要在本机创建。

Linux：

```bash
mkdir -p backup_demo/subdir
cp sample.log backup_demo/sample.log
cp config.json backup_demo/subdir/config.json
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Path .\backup_demo\subdir -Force
Copy-Item .\sample.log .\backup_demo\sample.log
Copy-Item .\config.json .\backup_demo\subdir\config.json
```

也可以将 backup.source 改为已有文件，例如 sample.log。

## 输出结果

- inspection.log：追加保存巡检记录。
- reports/log_analysis_时间戳.json：日志分析报告。
- backups/backup_时间戳/：本次备份目录。
- 本次备份目录中的 backup_record.json：备份源、目标、类型和记录时间。

如果备份内容本身名为 backup_record.json（忽略大小写），
记录文件改用 backup_record_meta.json，避免与备份内容冲突。
以终端输出的“备份记录”路径为准；已有记录不会被覆盖。

上述运行结果不纳入 Git 管理。

## 统计口径与当前限制

- 当前检查本机，不会通过 SSH 自动巡检其他服务器。
- Windows 默认检查 C 盘，Linux 默认检查根目录所在文件系统。
- Windows 跳过服务检查，进程查询目前仅支持 Linux。
- 网络数据是累计流量，不是实时网速。
- ps 输出的 CPU 百分比与整机短时间采样的 CPU 使用率口径不同。
- 日志分析采用不区分大小写的子串匹配，统计包含关键字的行数。
- 一行包含多个 ERROR 时，ERROR 行数只增加一次。
- 一行同时包含 ERROR 和 WARNING 时，两项行数分别增加一次。
- 匹配内容最多保存和展示前 20 条，但统计会读取完整文件。
- 单文件备份会比较复制前后的内容；目录备份尚未逐文件校验。
- 目录内部的符号链接按链接保存，不保证包含链接指向的数据。
- 备份不是一致性快照，暂不适合直接复制正在写入的数据库文件。

## 自动化测试

在项目根目录执行。

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Linux：

```bash
.venv/bin/python -m unittest discover -s tests -v
```

当前自动化测试覆盖：

- 日志关键字行数统计和匹配行号。
- 匹配内容只保留前 20 条，但继续统计完整文件。
- 日志文件不存在时的错误返回。
- 单文件备份的内容一致性。
- 目录备份对子目录、空目录及样例文件内容的保留。
- 拒绝将目录备份目标放在源目录自身或其内部。
- JSON 备份记录的位置和关键字段。
- 备份记录与源文件或目录重名时，保留备份内容并使用备用记录名。
- 服务加载状态或活动状态查询超时后，记录超时并继续检查其他服务。

当前共有 10 个测试方法。测试数据在临时目录中创建并自动清理；
服务超时测试使用模拟命令，不会启停本机服务。

## 样例日志的预期结果

运行日志分析命令后，sample.log 应得到：

- 总行数：7。
- ERROR 行数：3。
- WARNING 行数：2。
- 匹配行号：2、3、5、7。

## 验证情况

- 在新的 Python 3.12.14 虚拟环境中，按 requirements.txt 安装依赖，并在 Linux 检查环境运行全部 10 个自动化测试。
- 在 Windows 和 Ubuntu 的项目环境中运行全部 10 个自动化测试，结果均为 OK。
- 在 Windows 和 Ubuntu 实际运行资源巡检、日志分析和备份，功能正常；在 Ubuntu 验证了 Linux 服务检查及进程排序。
- 使用 sample.log 验证日志分析结果：总行数 7，ERROR 行数 3，WARNING 行数 2。
- 在临时检查环境中验证了从项目目录之外启动时的路径处理，以及常见错误的退出状态。