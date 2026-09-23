import psutil

cpu=psutil.cpu_percent(interval=1)

memory=psutil.virtual_memory().percent

print("=====系统状态=====")

print(f"CPU使用率:{cpu}%")

print(f"内存使用率:{memory}%")