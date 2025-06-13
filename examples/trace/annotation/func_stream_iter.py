# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from types import TracebackType
from typing import Iterator, Self, List
from cozeloop import flush
from cozeloop.decorator import observe


def process_iterator_output(output: List[str]):
    res = []
    for k in output:
        res.append(k)
    res.append('__end') # add end pointer, finally result: ['1', '2', '3', '4', '5', '__end']
    return res


@observe(
process_iterator_outputs=process_iterator_output
)
def iter_func():
    return Stream()


class Stream:
    def __init__(
            self,
    ) -> None:
        self._iterator = self.__stream__()

    def __next__(self) -> str:
        return self._iterator.__next__()

    def __iter__(self) -> Iterator[str]:
        for item in self._iterator:
            yield item

    def __stream__(self):
        res = ["1", "2", "3", "4", "5"]
        for event in res:
            yield event

    def __enter__(self) -> Self:
        return self

    def __exit__(
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

    print("start stream iter func")
    stream = iter_func()
    for item in stream:
        print(item)
    print("end stream iter func")

    # flush all trace data before server exit.
    flush()
