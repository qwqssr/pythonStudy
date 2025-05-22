import asyncio

async def say_hello_async():
    await asyncio.sleep(1)
    print("Hello, World!")

async def do_some_work_async():
    await asyncio.sleep(2)
    print("Doing some work...")