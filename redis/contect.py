import redis
import json

r = redis.Redis(
    host='117.72.198.89',
    port=6379,
    password='qwqssr',
    db=0,
    socket_connect_timeout=5
)

# 使用 JSON 存储字典
task = {"id": 1, "action": "download"}
r.lpush('task_queue', json.dumps(task))

# 消费时解析回来
data = r.rpop('task_queue')
if data:
    task_dict = json.loads(data)
    print(task_dict['action'])  # 输出: download
