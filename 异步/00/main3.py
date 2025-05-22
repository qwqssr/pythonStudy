import asyncio
import api


async def main():
    task = asyncio.create_task(
        api.fetch_data()
    )
    task.cancel()
    try:
        # task.done()
        result = await task
    except asyncio.CancelledError:
        print("Cancelled")
        pass
    except asyncio.TimeoutError:
        print("Timeout")

if __name__ == '__main__':
    asyncio.run(main())