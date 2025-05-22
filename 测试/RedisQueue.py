import json
import logging
from typing import (
    Generic, Iterable, List, Optional, Callable, TypeVar, Iterator, Any
)
import redis

T = TypeVar("T")


class RedisQueue(Generic[T]):
    """
    通用 Redis 队列，支持左右推送/弹出、批量操作、原子性批量弹出、队列搬迁、修剪、过期等功能。
    注意：__iter__ 会消费队列，__contains__ 全表扫描性能依赖队列大小。
    """
    _lua_pop_many = """
        local elements = {}
        local count = tonumber(ARGV[1])
        for i = 1, count do
            local elem = redis.call('LPOP', KEYS[1])
            if not elem then break end
            table.insert(elements, elem)
        end
        return elements
    """

    def __init__(
            self,
            *,
            host: str = "localhost",
            port: int = 6379,
            password: Optional[str] = None,
            db: int = 0,
            key: str = "default_queue",
            serialize: Callable[[T], bytes] = lambda x: json.dumps(x, ensure_ascii=False).encode("utf-8"),
            deserialize: Callable[[bytes], T] = lambda b: json.loads(b.decode("utf-8")),
            logger: Optional[logging.Logger] = None,
            **redis_kwargs: Any,
    ):
        """构造时传入 Redis 连接参数和序列化函数"""
        self.key = key
        self.serialize = serialize
        self.deserialize = deserialize
        self._redis = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=False,
            **redis_kwargs,
        )
        # 注册 Lua 脚本
        try:
            self._lua_script = self._redis.register_script(self._lua_pop_many)
        except redis.RedisError:
            self._lua_script = None

        # 初始化 Logger
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(self.__class__.__name__)
            self.logger.setLevel(logging.INFO)
            if not self.logger.hasHandlers():
                ch = logging.StreamHandler()
                ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
                self.logger.addHandler(ch)

    def push(
            self,
            item: T,
            side: str = "right",
    ) -> None:
        """向 left 或 right 方向推送单个元素"""
        if side not in ("left", "right"):
            raise ValueError("side must be 'left' or 'right'")
        cmd = self._redis.lpush if side == "left" else self._redis.rpush
        cmd(self.key, self.serialize(item))
        self.logger.info(f"push ({side}) 1 -> {self.key}")

    def push_many(
            self,
            items: Iterable[T],
            side: str = "right",
    ) -> int:
        """批量推送元素，返回实际推送数量"""
        if side not in ("left", "right"):
            raise ValueError("side must be 'left' or 'right'")
        pipe = self._redis.pipeline()
        cmd = pipe.lpush if side == "left" else pipe.rpush
        count = 0
        for i in items:
            cmd(self.key, self.serialize(i))
            count += 1
        pipe.execute()
        self.logger.info(f"push_many ({side}) {count} -> {self.key}")
        return count

    def pop(
            self,
            timeout: int = 0,
            side: str = "left",
    ) -> Optional[T]:
        """弹出元素，timeout>0 使用阻塞命令"""
        if side not in ("left", "right"):
            raise ValueError("side must be 'left' or 'right'")
        if timeout > 0:
            if side == "left":
                res = self._redis.blpop(self.key, timeout=timeout)
            else:
                res = self._redis.brpop(self.key, timeout=timeout)
            data = res[1] if res else None
        else:
            data = self._redis.lpop(self.key) if side == "left" else self._redis.rpop(self.key)
        if data is None:
            return None
        self.logger.info(f"pop ({side}) 1 <- {self.key}")
        return self.deserialize(data)

    def pop_many(self, count: int) -> List[T]:
        """原子性弹出多个元素，返回列表"""
        if count <= 0:
            return []
        if self._lua_script:
            raw = self._lua_script(keys=[self.key], args=[count])
        else:
            raw = []
            for _ in range(count):
                v = self._redis.lpop(self.key)
                if not v:
                    break
                raw.append(v)
        self.logger.info(f"pop_many {len(raw)} <- {self.key}")
        return [self.deserialize(v) for v in raw]

    def transfer(
            self,
            dest: str,
            timeout: int = 0,
    ) -> Optional[T]:
        """原子性转移本队尾到目标队首"""
        if timeout > 0:
            data = self._redis.brpoplpush(self.key, dest, timeout)
        else:
            data = self._redis.rpoplpush(self.key, dest)
        if data is None:
            return None
        self.logger.info(f"transfer 1: {self.key} -> {dest}")
        return self.deserialize(data)

    def peek_many(
            self,
            start: int = 0,
            end: int = -1,
    ) -> List[T]:
        """查看范围内所有元素，不消费"""
        raw = self._redis.lrange(self.key, start, end)
        return [self.deserialize(v) for v in raw]

    def trim(self, start: int, end: int) -> None:
        """保留指定区间元素，丢弃其余"""
        self._redis.ltrim(self.key, start, end)
        self.logger.info(f"trim {start}-{end} -> {self.key}")

    def expire(self, seconds: int) -> bool:
        """设置过期时间，返回是否成功"""
        ok = self._redis.expire(self.key, seconds)
        self.logger.info(f"expire {seconds}s -> {self.key}: {ok}")
        return ok

    def exists(self) -> bool:
        """检查队列是否存在"""
        return bool(self._redis.exists(self.key))

    def size(self) -> int:
        """返回队列长度"""
        n = self._redis.llen(self.key)
        self.logger.info(f"size {n} -> {self.key}")
        return n

    def clear(self) -> bool:
        """删除整个队列"""
        ok = bool(self._redis.delete(self.key))
        self.logger.info(f"clear -> {self.key}: {ok}")
        return ok

    def __len__(self) -> int:
        return self.size()

    def __contains__(self, item: T) -> bool:
        """存在性检查，性能依赖队列大小"""
        s = self.serialize(item)
        for v in self._redis.lrange(self.key, 0, -1):
            if v == s:
                return True
        return False

    def __iter__(self) -> Iterator[T]:
        """迭代访问并消费队列"""
        while True:
            v = self.pop()
            if v is None:
                break
            yield v

    def ping(self) -> bool:
        """测试 Redis 连接"""
        try:
            return self._redis.ping()
        except redis.RedisError:
            return False


# 使用示例
if __name__ == "__main__":
    # 初始化示例，注意替换为真实连接参数
    queue = RedisQueue[int](
        host="112.5.15.136",
        port=6379,
        password="redis_post_data",
        db=1,
        key="test_queue"
    )
    queue.clear()
    # 基本操作
    print("ping:", queue.ping())
    queue.push([1,2,34])
    # queue.push_many([2, 3, 4])
    # queue.pop()
    a = queue.peek_many()
    print(a)
    # print("pop:", queue.pop())
    # print("pop_many:", queue.pop_many(2))

    # # 高级功能
    # queue.push_many(list(range(10)), side="left")
    # queue.trim(0, 4)
    # print("peek_many:", queue.peek_many())
    #
    # # 转移到另一队列
    # backup = RedisQueue[int](host="112.5.15.136", port=6379, password="redis_post_data", db=1, key="backup")
    # item = queue.transfer(backup.key)
    # print("transferred:", item)
