# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
import time
from typing import Any

from cozeloop import new_client
from cozeloop.logger import set_log_level

logger = logging.getLogger(__name__)


class LLMRunner:
    def __init__(self, client):
        self.client = client

    def llm_call(self, input_data: Any):
        with self.client.start_span("llmCall", "model") as span:
            # Assuming llm is processing
            # os.environ['AZURE_OPENAI_API_KEY'] = 'xxx'  # need set a llm api key
            # os.environ[
            #     'OPENAI_API_VERSION'] = '2024-05-13'  # llm version, see more: https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#rest-api-versioning
            # os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://xxx'  # llm endpoint
            # os.environ['AUZURE_DEPLOYMENT'] = 'gpt-4o-2024-05-13'
            # output = AzureChatOpenAI(azure_deployment=os.environ['AUZURE_DEPLOYMENT']).invoke(input=input_data)

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
            span.set_start_time_first_resp(int(time.time() * 1000000))
            # set tag key: `input_tokens`
            span.set_input_tokens(input_token)
            # set tag key: `output_tokens`
            span.set_output_tokens(output_token)
            # set tag key: `model_name`, e.g., gpt-4-1106-preview, etc.
            span.set_model_name("gpt-4-1106-preview")

def get_large_text() -> str:
    # mock large text, >4M bytes
    size = 5 * 1024 * 1024  # 5MB
    res = "A" * size
    return res

def main():
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # COZELOOP_WORKSPACE_ID=your workspace id
    # COZELOOP_API_TOKEN=your token

    # 0. check switch !
    # To support ultra-large report, it is mandatory to set WithUltraLargeTraceReport(true)
    # when NewClient. Otherwise, the input or output of ultra-large text will be directly truncated.
    # Ultra-large trace report is only available for input and output.

    # 0. new client span
    set_log_level(logging.INFO)
    client = new_client(ultra_large_report=True)
    llm_runner = LLMRunner(client)

    # 1. start span
    with client.start_span("root_span", "main_span") as span:
        # 2. span set tag or baggage
        # set custom tag
        span.set_tags({
            "mode": "large_text",
            "node_id": 6076665,
            "node_process_duration": 228.6
        })

        # set custom baggage
        span.set_baggage({
            "product_id": "123456654321"
        })
        # set baggage key: `user_id`, implicitly set tag key: `user_id`
        span.set_user_id_baggage("123456")

        # assuming call llm, input is large text
        try:
            llm_runner.llm_call("你叫什么名字" + get_large_text())
        except Exception as e:
            # set tag key: `_status_code`
            span.set_status_code(600789111)
            # set tag key: `error`
            span.set_error(str(e))
            return

    # 3. (optional) flush or close
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
    main()