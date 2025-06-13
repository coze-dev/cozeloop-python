# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import asyncio
from cozeloop import flush
from cozeloop.decorator import observe


@observe()
async def fetch_data(biz_id: str):
    await asyncio.sleep(2)  # Simulate asynchronous I/O operations
    return biz_id + " Data"


@observe()
async def async_gen_func(biz_id: str, max):
    count = 1
    while count <= max:
        data = await fetch_data(biz_id)
        yield f"{data}, {count}"
        count += 1


@observe()
async def async_gen_main(biz_id: str, max):
    res = []
    async for value in async_gen_func(biz_id, max):
        res.append(value)
    return res


if __name__ == '__main__':
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # os.environ["COZELOOP_WORKSPACE_ID"] = "your workspace id"
    # os.environ["COZELOOP_API_TOKEN"] = "your token"

    print("start async gen func")
    async_gen_res = asyncio.run(async_gen_main("pe", 5))
    print(f"end async gen func, res:{async_gen_res}\n")

    # flush all trace data before server exit.
    flush()
