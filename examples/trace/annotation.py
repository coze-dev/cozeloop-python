import asyncio
from time import sleep
from types import TracebackType
from typing import Iterator, Self, AsyncIterator, List

from cozeloop import flush, new_client
from cozeloop._client import set_default_client

from cozeloop.decorator import observe


def change_input(input: dict):
    input["xxx1"] = "yyy1"
    return input


def change_output(output: tuple):
    res = {}
    for k in output:
        res[k] = k
    res["xxx2"] = "yyy2"
    return res


@observe(
    # client=new_client(api_token="111222333"),  # assign client, priority is higher than the default client
    name="new_name",  # assign span name
    span_type="my_type",  # assign span type
    tags={"t_tag1": "t_value1", "t_tag2": 2},  # assign tags
    process_inputs=change_input,  # process inputs result before report trace
    process_outputs=change_output  # process outputs result before report trace
)
def normal_function(a, b, c=1):
    return normal_function_son1(a, b, c) + normal_function_son2(a, b, c)


@observe()
def normal_function_son1(a, b, c=1):
    return a + b + c, b + c


@observe()
def normal_function_son2(a, b, c=1):
    return a + b + c, b + c


##################################

@observe()
async def fetch_data(biz_id: str):
    await asyncio.sleep(2)  # Simulate asynchronous I/O operations
    return biz_id + " Data"


@observe()
async def async_func(biz_id: str):
    data = await fetch_data(biz_id)
    return data


##################################

@observe()
def gen_func(max):
    count = 1
    while count <= max:
        yield count
        count += 1


##################################

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


##################################

def process_iterator_output(output: List[str]):
    res = []
    for k in output:
        res.append(k)
    res.append("I am func of process iterator output")
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


##################################

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

    # set global default client, don't need to pass the client parameter when adding annotations subsequently.
    set_default_client(new_client())

    # normal func
    print("start normal func")
    result = normal_function(2, 3, c=4)
    print(f"end normal func, res:{result}\n")
    #
    # # async func
    # print("start async func")
    # async_result = asyncio.run(async_func("pe"))
    # print(f"end async func, res:{async_result}\n")
    #
    # # generator func
    # print("start gen func")
    # gen = gen_func(5)
    # print(next(gen))
    # print(next(gen))
    # print(next(gen))
    # print(next(gen))
    # print(next(gen))
    # gen.close()
    # print("end gen func\n")
    #
    # # async generator func
    # print("start async gen func")
    # async_gen_res = asyncio.run(async_gen_main("pe", 5))
    # print(f"end async gen func, res:{async_gen_res}\n")

    # # stream iter func
    # print("start stream iter func")
    # stream = iter_func()
    # for item in stream:
    #     print(item)
    # print("end stream iter func")
    #
    # # async stream iter func
    # print("start async stream iter func")
    # asyncio.run(async_iter_main())
    # print("end async stream iter func")

    flush()
