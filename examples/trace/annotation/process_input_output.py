# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from cozeloop import flush
from cozeloop.decorator import observe

# The input is a dictionary with the format: {"args": args, "kwargs": kwargs}, args is tuple, kwargs is dict
def change_input(input: dict):
    print(f"change_input src input:{input}")
    args = input['args'] # args is [2, 3]
    a = args[0]
    b = args[1]
    kwargs = input['kwargs'] # kwargs is {'c': 4}
    c = kwargs['c']

    res = {
        'a': a,
        'b': b,
        'c': c,
    }

    return res

# For regular functions, the input is Any (the original function result). For generator functions, after being fully
# consumed or closed, the result will be packaged into a List. If the generator is not fully consumed or closed,
# it's considered unfinished, the result will be empty, and no output will be reported.
def change_output(output: tuple):
    res = {'result': output}
    return res


@observe(
    process_inputs=change_input,  # process inputs result before report trace
    process_outputs=change_output  # process outputs result before report trace
)
def normal_function(a, b, c=1):
    return add(a, b, c) + multiplication(a, b, c)


@observe()
def add(a, b, c=1):
    return a + b + c


@observe()
def multiplication(a, b, c=1):
    return a * b * c



if __name__ == '__main__':
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # os.environ["COZELOOP_WORKSPACE_ID"] = "your workspace id"
    # os.environ["COZELOOP_API_TOKEN"] = "your token"

    print("start normal func")
    result = normal_function(2, 3, c=4)
    print(f"end normal func, res:{result}\n")

    # flush all trace data before server exit.
    flush()
