# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
import time

from cozeloop import new_client, flush
from cozeloop.decorator import observe
from cozeloop.logger import set_log_level

logger = logging.getLogger(__name__)

ERR_CODE_LLM_CALL = 600789111

class LLMRunner:
    def __init__(self):
        pass

    @observe(
        name="llmCall",
        span_type="model",
        tags={"model_provider":'openai', "input_tokens": 232, "output_tokens": 1211, "model_name": "gpt-4-1106-preview"},
    )
    def llm_call(self, input_data):
        """
        Simulate an LLM call and set relevant span tags.
        """
        # span = self.client.start_span("llmCall", "model")
        try:
            # Assuming llm is processing
            # output = ChatOpenAI().invoke(input=input_data)

            # mock resp
            time.sleep(1)
            output = "I'm a robot. I don't have a specific name. You can give me one."
            return output
        except Exception as e:
            raise e
        finally:
            pass

@observe(
    # client=new_client(api_token="**"), # Unless you need a new client, no configuration is required,
                                         # the default client will be used automatically.
    name="root_span",                    # The name of the Span. Defaults to the function name.
    span_type="main_span",               # The span_type of the Span. Defaults to 'custom'.
    tags={"mode": 'simple', "node_id": 6076665},  # Set custom tag. The Priority is higher than the default tags.
    baggage={"product_id": "123456654321"},  # Set custom baggage. baggage can cover tag of sample key, and will pass to child span automatically.
)
def do_simple_demo():
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # os.environ["COZELOOP_WORKSPACE_ID"] = "your workspace id"
    # os.environ["COZELOOP_API_TOKEN"] = "your token"

    # 0. new client
    set_log_level(logging.INFO)
    llm_runner = LLMRunner()

    # assuming call llm
    try:
        # assuming call llm
        llm_runner.llm_call("What's your name?")
    except Exception as e:
        pass


if __name__ == "__main__":
    do_simple_demo()

    # flush all trace data before server exit.
    flush()