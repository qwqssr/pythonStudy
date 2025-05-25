import asyncio
import random
import time

from DrissionPage import Chromium,ChromiumOptions,SessionPage
from Flet.APP01 import CrawlerApp
import flet as ft

co = ChromiumOptions()
# co.auto_port(True)
co.set_local_port(9888)
# --process-per-tab
co.set_argument('--process-per-tab')
# browser = Chromium(co)

page = SessionPage()
def test(self, url):

    # tab = browser.new_tab()
    page.get(url)
    try:

        title = page.ele('#category-data').text
        print(title)
        return True
    except Exception as e:

        title = page.title
        print("错误",e)
        return False
    finally:
        pass
        # tab.close()


if __name__ == "__main__":
    async def main():
        app = CrawlerApp()
        app._sync_do_main = test.__get__(app, CrawlerApp)
        await ft.app_async(
            target=app.initialize,
            view=ft.FLET_APP
        )
    asyncio.run(main())