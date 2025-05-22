import asyncio
import random
import time
import os
import sys
import io
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import flet as ft


@dataclass
class CrawlerConfig:
    process_count: int = 3
    retry_count: int = 0
    retry_interval: float = 1.0

    def update(self, process_count: int, retry_count: int, interval: float):
        self.process_count = process_count
        self.retry_count = retry_count
        self.retry_interval = interval

    def __str__(self):
        return (
            f"并发数: {self.process_count}\n"
            f"重试次数: {self.retry_count}\n"
            f"重试间隔: {self.retry_interval} 秒"
        )


class TextIOWrapper(io.TextIOBase):
    def __init__(self, page):
        self.page = page
        self.original_stdout = sys.stdout

    def write(self, text):
        if text.strip() and not getattr(self, "_in_write", False):
            try:
                self._in_write = True
                self.original_stdout.write(text.rstrip('\n') + '\n')
                self.original_stdout.flush()
                self.page.loop.call_soon_threadsafe(
                    lambda: self.page.pubsub.send_all({
                        "type": "log",
                        "data": {"message": text.strip()}
                    })
                )
            except Exception as e:
                self.original_stdout.write(f"[Log Error] {str(e)}\n")
                self.original_stdout.flush()
            finally:
                self._in_write = False


class CrawlerApp:
    def __init__(self):
        self.config = CrawlerConfig()
        self.is_running = False
        self.is_timing = False
        self.start_time = 0.0
        self.global_semaphore: Optional[asyncio.Semaphore] = None
        self.page: Optional[ft.Page] = None
        self.timer_task: Optional[asyncio.Task] = None

    def create_config_view(self):
        return ft.Column([
            ft.Text("⚙️ 当前配置", style=ft.TextThemeStyle.TITLE_MEDIUM),
            ft.Text(f"并发数: {self.config.process_count}", selectable=True),
            ft.Text(f"重试次数: {self.config.retry_count}", selectable=True),
            ft.Text(f"重试间隔: {self.config.retry_interval} 秒", selectable=True),
        ], width=200, height=150)

    def refresh_semaphore(self):
        self.global_semaphore = asyncio.Semaphore(self.config.process_count)

    def send_update(self, type_: str, **kwargs):
        self.page.pubsub.send_all({"type": type_, "data": kwargs})

    async def do_main(self, url):
        await asyncio.sleep(self.config.retry_interval)
        if random.random() <= 0.2:
            print("发生异常")
            raise Exception("模拟异常")
        return True

    async def crawl_single_url(self, url: str, idx: int, total: int):
        try:
            await self.global_semaphore.acquire()
        except (asyncio.CancelledError, Exception):
            return

        if not self.is_running:
            self.global_semaphore.release()
            return

        try:
            await self.do_main(url)
            success = True
        except Exception as e:
            self.send_update("error", message=f"[{idx}/{total}] {url} 采集失败: {str(e)}")
            success = False

        self.send_update("result", url=url, success=success)
        self.send_update("progress", value=idx / total)
        self.send_update("status", value=f"正在爬取 ({idx}/{total}): {url}")

        try:
            self.global_semaphore.release()
        except:
            pass

    async def process_crawl_results(self, urls: List[str]):
        total = len(urls)
        self.send_update("progress", value=0)
        self.send_update("status", value="开始爬取...")

        tasks = [
            self.crawl_single_url(url, i + 1, total)
            for i, url in enumerate(urls)
        ]

        batch_size = self.config.process_count
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            await asyncio.gather(*batch)
            await asyncio.sleep(0.1)

        self.send_update("status", value="爬取完成！" if self.is_running else "已终止运行")
        self.is_running = False
        self.is_timing = False

    async def update_timer(self):
        """更新计时器的异步任务"""
        while self.is_timing:
            try:
                elapsed = time.time() - self.start_time
                # 使用pubsub发送计时器更新消息
                self.send_update("timer", elapsed=elapsed)
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Timer update error: {e}")
                break

    async def start_crawling(self, e):
        self.tab_control.selected_index = 0
        self.switch_tab(None)

        file_path = self.file_input.value
        if not file_path or not os.path.exists(file_path):
            self.send_update("status", value="请先选择有效的 txt 文件")
            return

        # 停止之前的计时器任务
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()

        self.start_time = time.time()
        self.is_timing = True
        self.is_running = True

        # 启动计时器任务
        self.timer_task = asyncio.create_task(self.update_timer())

        # 清理UI状态
        self.log_view.controls.clear()
        self.success_list.controls.clear()
        self.failed_list.controls.clear()
        self.success_count.value = "0"
        self.failed_count.value = "0"
        self.progress.value = 0
        self.time_counter.value = "运行时间: 0.0秒"
        self.page.update()

        self.send_update("log", message=f"⚙️ 当前配置:\n{str(self.config)}")

        with open(file_path, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]

        self.refresh_semaphore()

        async def refresh_task():
            while self.is_running:
                await asyncio.sleep(0.1)
                try:
                    self.page.update()
                except:
                    pass

        asyncio.create_task(refresh_task())
        asyncio.create_task(self.process_crawl_results(urls))

    def stop_crawling(self, e):
        self.is_running = False
        self.is_timing = False

        # 取消计时器任务
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()

        self.send_update("status", value="正在停止...")

    def handle_file_pick(self, e):
        self.file_picker.pick_files(allowed_extensions=["txt"])

    def handle_file_result(self, e: ft.FilePickerResultEvent):
        if e.files:
            self.file_input.value = e.files[0].path
            self.page.update()

    def update_theme(self, e):
        mode = self.theme_dropdown.value
        if mode == "dark":
            self.page.bgcolor = None
            self.page.theme_mode = ft.ThemeMode.DARK
        elif mode == "eye_care":
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.page.bgcolor = ft.Colors.GREEN_50
        else:
            self.page.bgcolor = None
            self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.update()

    def update_config(self, e):
        try:
            new_config = {
                "process_count": int(self.process_dropdown.value),
                "retry_count": int(self.retry_dropdown.value),
                "interval": float(self.interval_input.value)
            }
            self.config.update(**new_config)
            self.refresh_semaphore()
            self.send_update("log", message="⚙️ 配置已更新")
        except Exception as ex:
            self.send_update("error", message=f"配置更新失败: {ex}")

    def switch_tab(self, e):
        self.content_area.controls.clear()
        if self.tab_control.selected_index == 0:
            self.config_container.content = self.create_config_view()
            self.content_area.controls.append(self.main_view)
        else:
            self.content_area.controls.append(self.settings_view)
        self.page.update()

    async def on_pubsub_message(self, msg: Dict[str, Any]):
        msg_type = msg["type"]
        data = msg["data"]

        if msg_type == "progress" and self.progress.page is not None:
            self.progress.value = data["value"]
            await self.progress.update_async()

        elif msg_type == "status" and self.status.page is not None:
            self.status.value = data["value"]
            await self.status.update_async()

        elif msg_type == "timer" and self.time_counter.page is not None:
            # 处理计时器更新消息
            elapsed = data["elapsed"]
            d, r = divmod(elapsed, 86400)
            h, r = divmod(r, 3600)
            m, s = divmod(r, 60)
            parts = []
            if d: parts.append(f"{int(d)}天")
            if h: parts.append(f"{int(h)}小时")
            if m: parts.append(f"{int(m)}分")
            self.time_counter.value = f"运行时间: {''.join(parts)}{s:.1f}秒"
            # self.time_counter.value = f"运行时间: {elapsed:.1f}秒"
            await self.time_counter.update_async()

        elif msg_type == "log":
            self.log_view.controls.append(ft.Text(data["message"], selectable=True))
            if len(self.log_view.controls) > 100:
                self.log_view.controls.pop(0)
            await self.log_view.update_async()

        elif msg_type == "result" and self.success_list.page is not None:
            target_list = self.success_list if data["success"] else self.failed_list
            target_list.controls.append(ft.Text(data["url"], selectable=True))

            stat = self.success_count if data["success"] else self.failed_count
            stat.value = str(len(target_list.controls))
            await stat.update_async()

            await target_list.update_async()

        elif msg_type == "error":
            print(f"[ERROR] {data['message']}")

        elif msg_type == "config":
            self.config.update(**data)
            await self.send_update("log", message="⚙️ 配置已更新")

    def create_ui_components(self):
        # 创建 UI 组件
        self.file_input = ft.TextField(label="选择txt文件", expand=True, read_only=True)
        self.file_button = ft.ElevatedButton("选择文件")
        self.progress = ft.ProgressBar(width=400)
        self.status = ft.Text("等待开始...")
        self.success_list = ft.ListView(height=120, auto_scroll=True)
        self.failed_list = ft.ListView(height=120, auto_scroll=True)
        self.log_view = ft.ListView(height=200, auto_scroll=True)
        self.config_container = ft.Container(content=self.create_config_view())
        self.time_counter = ft.Text("运行时间: 0.0秒", key="time_counter")

        # 统计标签
        self.success_count = ft.Text("0", size=16, color=ft.Colors.GREEN, key="success_count")
        self.failed_count = ft.Text("0", size=16, color=ft.Colors.RED, key="failed_count")

        # 控制按钮
        self.start_button = ft.FilledTonalButton("开始爬取", icon="play_arrow", on_click=self.start_crawling)
        self.stop_button = ft.FilledTonalButton("停止爬取", icon="stop", on_click=self.stop_crawling)

        # 文件选择器
        self.file_picker = ft.FilePicker(on_result=self.handle_file_result)
        self.file_button.on_click = self.handle_file_pick

        # 设置组件
        self.theme_dropdown = ft.Dropdown(
            label="主题模式",
            options=[
                ft.dropdown.Option("default", "默认"),
                ft.dropdown.Option("dark", "夜间"),
                ft.dropdown.Option("eye_care", "护眼")
            ],
            value="default",
            width=200
        )
        self.retry_dropdown = ft.Dropdown(
            label="重试次数",
            options=[ft.dropdown.Option(str(i)) for i in range(0, 6)],
            value=str(self.config.retry_count),
            width=150
        )
        self.process_dropdown = ft.Dropdown(
            label="并发数",
            options=[ft.dropdown.Option(str(i)) for i in range(1, 17)],
            value=str(self.config.process_count),
            width=150
        )
        self.interval_input = ft.TextField(
            label="重试间隔 (秒)",
            value=str(self.config.retry_interval),
            width=150
        )

        # 绑定事件处理器
        self.theme_dropdown.on_change = self.update_theme
        self.retry_dropdown.on_change = self.update_config
        self.process_dropdown.on_change = self.update_config
        self.interval_input.on_change = self.update_config

    def create_views(self):
        # 主视图
        self.main_view = ft.Column([
            ft.Row([self.file_input, self.file_button]),
            ft.Row([self.start_button, self.stop_button]),
            ft.Container(height=10),
            ft.Row([self.progress, self.time_counter]),
            self.status,
            ft.Container(height=10),
            ft.Row([
                ft.Column([
                    ft.Row([
                        ft.Text("✅ 成功的 URL", style=ft.TextThemeStyle.TITLE_MEDIUM),
                        self.success_count
                    ]),
                    self.success_list
                ], width=450, height=150),
                ft.Column([
                    ft.Row([
                        ft.Text("❌ 失败的 URL", style=ft.TextThemeStyle.TITLE_MEDIUM),
                        self.failed_count
                    ]),
                    self.failed_list
                ], width=450, height=150),
                self.config_container
            ]),
            ft.Divider(),
            ft.Text("日志输出：", style=ft.TextThemeStyle.LABEL_LARGE),
            self.log_view
        ], scroll=ft.ScrollMode.AUTO)

        # 设置视图
        self.settings_view = ft.Column([
            ft.Text("设置", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
            self.theme_dropdown,
            ft.Row([self.retry_dropdown, self.interval_input, self.process_dropdown])
        ])

        # 标签页
        self.tab_control = ft.Tabs(
            selected_index=0,
            tabs=[ft.Tab(text="主界面"), ft.Tab(text="设置")],
            expand=0
        )
        self.content_area = ft.Column()
        self.main_container = ft.Column([self.tab_control, self.content_area], expand=True)

    async def initialize(self, page: ft.Page):
        self.page = page
        self.page.title = "简单爬虫工具"
        self.page.padding = 20
        self.page.theme_mode = ft.ThemeMode.LIGHT

        # 创建所有UI组件
        self.create_ui_components()
        self.create_views()

        # 设置标签页切换事件
        self.tab_control.on_change = self.switch_tab

        # 添加文件选择器到页面
        self.page.overlay.append(self.file_picker)

        # 添加主容器到页面
        self.page.add(self.main_container)

        # 初始显示主视图
        self.content_area.controls.append(self.main_view)
        self.page.update()

        # 订阅消息
        self.page.pubsub.subscribe(self.on_pubsub_message)

        # 重定向输出
        sys.stdout = TextIOWrapper(self.page)
        sys.stderr = TextIOWrapper(self.page)


async def main():
    app = CrawlerApp()
    await ft.app_async(
        target=app.initialize,
        view=ft.FLET_APP
    )


if __name__ == "__main__":
    asyncio.run(main())