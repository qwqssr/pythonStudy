import asyncio
import random
import time

from DrissionPage import Chromium,ChromiumOptions
from Flet.APP01 import CrawlerApp
import flet as ft

co = ChromiumOptions()
# co.auto_port(True)
co.set_local_port(9888)

co.set_argument('--process-per-tab') # 设置每个标签页都是一个进程
browser = Chromium(co)
def test(self, url):

    tab = browser.new_tab()

    try:
        tab.get(url)
        time.sleep(3)
        if random.random() < 0.9:
            print("你好,通过")
            return True
        else:
            print("你好,不通过")
            return False
    finally:
        tab.close()


if __name__ == "__main__":
    async def main():
        app = CrawlerApp()
        app._sync_do_main = test.__get__(app, CrawlerApp)
        await ft.app_async(
            target=app.initialize,
            view=ft.FLET_APP
        )
    asyncio.run(main())