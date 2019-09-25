import asyncio

async def inner():
    print("starting")
    asyncio.sleep(5)
    print("done")
    return 4

async def main():
    task = asyncio.ensure_future(inner())
    asyncio.sleep(10)
    await task

asyncio.run(main)

