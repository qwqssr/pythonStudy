import asyncio

async def fetch_data():
    print('fetching data')
    await asyncio.sleep(2)

    print('data fetched')

    return 'Api Data'

