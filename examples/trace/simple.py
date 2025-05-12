# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
import time

from cozeloop import new_client
from cozeloop.logger import set_log_level

logger = logging.getLogger(__name__)

ERR_CODE_LLM_CALL = 600789111

class LLMRunner:
    def __init__(self, client):
        self.client = client

    def llm_call(self, input_data):
        """
        Simulate an LLM call and set relevant span tags.
        """
        span = self.client.start_span("llmCall", "model")
        try:
            # Assuming llm is processing
            # output = ChatOpenAI().invoke(input=input_data)

            # mock resp
            time.sleep(1)
            output = "I'm a robot. I don't have a specific name. You can give me one."
            input_token = 232
            output_token = 1211

            # set tag key: `input`
            span.set_input(input_data)
            # set tag key: `output`
            span.set_output(output)
            # set tag key: `model_provider`, e.g., openai, etc.
            span.set_model_provider("openai")
            # set tag key: `start_time_first_resp`
            # Timestamp of the first packet return from LLM, unit: microseconds.
            # When `start_time_first_resp` is set, a tag named `latency_first_resp` calculated
            # based on the span's StartTime will be added, meaning the latency for the first packet.
            span.set_start_time_first_resp(int(time.time() * 1000000))
            # set tag key: `input_tokens`. The amount of input tokens.
            # when the `input_tokens` value is set, it will automatically sum with the `output_tokens` to calculate the `tokens` tag.
            span.set_input_tokens(input_token)
            # set tag key: `output_tokens`. The amount of output tokens.
            # when the `output_tokens` value is set, it will automatically sum with the `input_tokens` to calculate the `tokens` tag.
            span.set_output_tokens(output_token)
            # set tag key: `model_name`, e.g., gpt-4-1106-preview, etc.
            span.set_model_name("gpt-4-1106-preview")

            return None
        except Exception as e:
            raise e
        finally:
            span.finish()


def do_simple_demo():
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # os.environ["COZELOOP_WORKSPACE_ID"] = "your workspace id"
    # os.environ["COZELOOP_API_TOKEN"] = "your token"

    # 0. new client
    set_log_level(logging.INFO)
    client = new_client()
    llm_runner = LLMRunner(client)

    # 1. start span
    span = client.start_span("root_span", "main_span")

    # 2. span set tag or baggage
    # set custom tag
    span.set_tags({
        "mode":                  "simple",
		"node_id":               6076665,
		"node_process_duration": 228.6,
        "is_first_node":         True,
    })

    # set custom baggage, baggage can cover tag of sample key, and baggage will pass to child span automatically.
    span.set_baggage({
        "product_id": "123456654321",  # Assuming product_id is global field
    })
    # set baggage key: `user_id`, implicitly set tag key: `user_id`
    span.set_user_id_baggage("123456")

    # assuming call llm
    try:
        # assuming call llm
        llm_runner.llm_call("What's your name?")
    except Exception as e:
        # set tag key: `_status_code`
        span.set_status_code(ERR_CODE_LLM_CALL)
        # set tag key: `error`, if `_status_code` value is not defined, `_status_code` value will be set -1.
        span.set_error(str(e))

    # 3. span finish
    span.finish()

    # 4. (optional) flush or close
    # -- force flush, report all traces in the queue
    # Warning! In general, this method is not needed to be call, as spans will be automatically reported in batches.
    # Note that flush will block and wait for the report to complete, and it may cause frequent reporting,
    # affecting performance.
    client.flush()

    # -- close trace, do flush and close client
    # Warning! Once Close is executed, the client will become unavailable and a new client needs
    # to be created via NewClient! Use it only when you need to release resources, such as shutting down an instance!
    # client.close()


if __name__ == "__main__":
    do_simple_demo()