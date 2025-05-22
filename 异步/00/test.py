import time

import requests
from requests import Response

import asyncio
from asyncio import Task

def tongbu(url,num):
    response = requests.get(url)
    print(f'wait {num} seconds')
    time.sleep(num)
    return response

async def fetch_status(url, num):
    print("Fetching status for {}".format(url))
    response = await asyncio.to_thread(tongbu, url,num)
    print("Done")
    return {'status': response.status_code,'url': url}

async def main():
    # apple_task = asyncio.create_task(fetch_status("https://www.apple.com/",1))
    # google_task = asyncio.create_task(fetch_status("https://www.google.com/",2))
    #
    # apple_status = await apple_task
    # google_status = await google_task
    #
    # print(apple_status)
    # print(google_status)

#     如果不关心并发限制
    urls = [
        ("https://www.apple.com/ ", 1),
        ("https://www.google.com/ ", 1),
        ("https://www.google.com/ ", 1),
        # 更多任务...
    ]

    tasks = [fetch_status(url, num) for url, num in urls]
    results = await asyncio.gather(*tasks)
    print(results)
if __name__ == '__main__':
    asyncio.run(main=main())