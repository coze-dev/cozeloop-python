# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from cozeloop import flush
from cozeloop.decorator import observe

@observe()
def gen_func(max):
    count = 1
    while count <= max:
        yield count
        count += 1


if __name__ == '__main__':
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # os.environ["COZELOOP_WORKSPACE_ID"] = "your workspace id"
    # os.environ["COZELOOP_API_TOKEN"] = "your token"

    print("start gen func")
    gen = gen_func(5)
    print(next(gen))
    print(next(gen))
    print(next(gen))
    print(next(gen))
    print(next(gen))
    # The output will only be report when the generator is fully consumed (raising StopIteration) or closed,
    # which marks the function's completion.
    gen.close()
    print("end gen func\n")

    # flush all trace data before server exit.
    flush()
