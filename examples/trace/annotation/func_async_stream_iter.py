# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import asyncio
from types import TracebackType
from typing import Self, AsyncIterator, List
from cozeloop import flush
from cozeloop.decorator import observe


def process_iterator_output(output: List[str]):
    res = []
    for k in output:
        res.append(k)
    return res


@observe()
async def async_iter_main():
    res = await async_iter_func()
    async for item in res:
        print(item)


@observe(
    process_iterator_outputs=process_iterator_output
)
async def async_iter_func():
    return AsyncStream()


class AsyncStream:
    def __init__(
            self,
    ) -> None:
        self._iterator = self.__stream__()

    async def __anext__(self) -> str:
        return self._iterator.__next__()

    async def __aiter__(self) -> AsyncIterator[str]:
        for item in self._iterator:
            yield item

    def __stream__(self):
        res = ["1", "2", "3", "4", "5"]
        for event in res:
            yield event

    async def __aenter__(self) -> Self:
        pass

    async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            exc_tb: TracebackType | None,
    ) -> None:
        pass


if __name__ == '__main__':
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # os.environ["COZELOOP_WORKSPACE_ID"] = "your workspace id"
    # os.environ["COZELOOP_API_TOKEN"] = "your token"

    print("start async stream iter func")
    asyncio.run(async_iter_main())
    print("end async stream iter func")

    # flush all trace data before server exit.
    flush()
