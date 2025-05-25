import redis
import json

r = redis.Redis(host='117.72.198.89', port=6379, password='qwqssr')
r.xgroup_create('workstream', 'worker_group', id='$', mkstream=True)

while True:
    stream = r.xreadgroup('worker_group', 'worker1', {'workstream': '>'}, count=1, block=0)
    if stream:
        for _, entries in stream:
            for entry_id, data in entries:
                task_dict = json.loads(data[b'data'])
                print("收到任务:", task_dict)
                r.xack('workstream', 'worker_group', entry_id)
