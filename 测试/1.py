from togou import SafeFileWriter

from togou import SafeFileWriter
from concurrent.futures import ProcessPoolExecutor
import os

# Redis 配置
DEFAULT_REDIS_CONFIG = [
    {
        "host": '112.5.15.136',
        "port": 6379,
        "password": 'redis_post_data',
        "db": 1,
    }
]

# 创建 writer 实例
writer = SafeFileWriter(redis_servers=DEFAULT_REDIS_CONFIG)

# 注意：由于 multiprocessing 每个进程都是独立的，你需要在每个进程中重新初始化 writer，
# 否则可能遇到 Pickling 错误或全局变量问题。
def process_write(i):
    local_writer = SafeFileWriter(redis_servers=DEFAULT_REDIS_CONFIG)
    print(f"[PID: {os.getpid()}] 当前写入 {i}")
    lines = [f"Line {i}" for i in range(1000)]
    writer.write_lines("process_test.txt", lines)


def test_process_writes(max_workers=4, total_tasks=2000):
    print(f"=== 开始多进程写入测试（最多 {max_workers} 个进程） ===")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_write, i) for i in range(total_tasks)]
        for future in futures:
            future.result()  # 等待所有任务完成

    print("写入完成，检查文件内容...")
    with open("process_test.txt", "r") as f:
        lines = f.readlines()
        print(f"📄 总共写入了 {len(lines)} 行内容")
        assert len(lines) == total_tasks*1000, "❌ 写入行数不对，可能有冲突或丢失！"
    print("✅ 多进程写入测试通过！")


if __name__ == "__main__":
    test_process_writes(max_workers=10, total_tasks=100)

    # ✅ 多进程写入测试通过！
    # 38.62838839998585