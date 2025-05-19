import asyncio
import api

async def send_data(to):
    print("sending data to {}".format(to))
    await asyncio.sleep(2)
    print("Data sent to {}".format(to))

async def main():
    data = await api.fetch_data()
    print('Data:', data)
    await asyncio.gather(send_data("Mario"), send_data("Luigi"), send_data("Suir"))

if __name__ == '__main__':
    asyncio.run(main())