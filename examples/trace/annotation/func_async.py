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
async def async_func(biz_id: str):
    data = await fetch_data(biz_id)
    return data


if __name__ == '__main__':
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # os.environ["COZELOOP_WORKSPACE_ID"] = "your workspace id"
    # os.environ["COZELOOP_API_TOKEN"] = "your token"

    print("start async func")
    async_result = asyncio.run(async_func("pe"))
    print(f"end async func, res:{async_result}\n")

    # flush all trace data before server exit.
    flush()
