import redis
import json
import time

from contextlib import closing

with closing(redis.Redis(
    host='117.72.198.89',
    port=6379,
    password='qwqssr'
)) as r:
    for i in range(5):
        task = {
            'job_id': i,
            'type': 'task',
            'user': 'alice',
            'priority': 1
        }
        r.xadd('workstream', fields={'data': json.dumps(task)})
        time.sleep(1)
# 程序结束时自动关闭连接 ✅
