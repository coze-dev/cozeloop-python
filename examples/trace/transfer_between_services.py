# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import time
from datetime import datetime
from typing import Optional, Dict, Any, Union
import logging

from cozeloop import new_client, get_span_from_header
from cozeloop.logger import set_log_level

logger = logging.getLogger(__name__)

ERR_CODE_LLM_CALL = 600789111
ERR_CODE_INTERNAL = 600789112


class LLMRunner:
    def __init__(self, client):
        self.client = client

    def llm_call(self, input_data: Optional[Any] = None) -> Optional[Exception]:
        """
        Simulate an LLM call and set relevant span tags.
        """

        # modelSpan is child of rootSpan by ctx
        with self.client.start_span("llmCall", "model") as model_span:
            # Assuming llm is processing
            # output = ChatOpenAI().invoke(input=input_data)


            # mock resp
            time.sleep(1)
            output = "I'm a robot. I don't have a specific name. You can give me one."
            input_token = 232
            output_token = 1211

            # set tag key: `input`
            model_span.set_input(input_data)
            # set tag key: `output`
            model_span.set_output(output)
            # set tag key: `model_provider`, e.g., openai, etc.
            model_span.set_model_provider("openai")
            # set tag key: `start_time_first_resp`
            # Timestamp of the first packet return from LLM, unit: microseconds.
            # When `start_time_first_resp` is set, a tag named `latency_first_resp` calculated
            # based on the modelSpan's StartTime will be added, meaning the latency for the first packet.
            model_span.set_start_time_first_resp(int(datetime.now().timestamp() * 1000000))
            # set tag key: `input_tokens`. The amount of input tokens.
            # when the `input_tokens` value is set, it will automatically sum with the `output_tokens` to calculate the `tokens` tag.
            model_span.set_input_tokens(input_token)
            # set tag key: `output_tokens`. The amount of output tokens.
            # when the `output_tokens` value is set, it will automatically sum with the `input_tokens` to calculate the `tokens` tag.
            model_span.set_output_tokens(output_token)
            # set tag key: `model_name`, e.g., gpt-4-1106-preview, etc.
            model_span.set_model_name("gpt-4-1106-preview")

        return None

    def invoke_service_b(self, req_header: Dict[str, str]):
        """
        Assuming anotherService is another service.
        """

        # 1. start rootSpan of service B,
        span_context = get_span_from_header(req_header)
        root_span_b = self.client.start_span("root_span_serviceB", "main_span", child_of=span_context)

        # 2. rootSpan set tag or baggage
        # set custom tag
        root_span.set_tags({"service_name": "serviceB"})
        # do something...

        # 3. finish
        root_span_b.finish()


if __name__ == "__main__":
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # os.environ["COZELOOP_WORKSPACE_ID"] = "your workspace id"
    # os.environ["COZELOOP_API_TOKEN"] = "your token"

    # 0. new client
    set_log_level(logging.INFO)
    client = new_client()
    llm_runner = LLMRunner(client)

    # 1. start rootSpan, because there is no rootSpan in the so parentSpan is root rootSpan of new trace
    root_span = client.start_span("root_span_serviceA", "main_span")

    # 2. rootSpan set tag or baggage
    # set custom tag
    root_span.set_tags({"service_name": "serviceA"})

    # set custom baggage, baggage can cover tag of sample key, and baggage will pass to child rootSpan automatically.
    root_span.set_baggage({
        "product_id": "123456654321",  # Assuming product_id is global field, need to be passed to child rootSpan automatically.
        "product_name": "AI bot",  # Assuming product_name is global field, need to be passed to child rootSpan automatically.
        "product_version": "0.0.1",  # Assuming product_version is global field, need to be passed to child rootSpan automatically.
    })
    # set baggage key: `user_id`, implicitly set tag key: `user_id`
    root_span.set_user_id_baggage("123456")

    # assuming call llm
    err = llm_runner.llm_call("What's your name?")
    if err is not None:
        # set tag key: `_status_code`
        root_span.set_status_code(ERR_CODE_LLM_CALL)
        # set tag key: `error`, if `_status_code` value is not defined, `_status_code` value will be set -1.
        root_span.set_error(str(err))
        exit(1)

    header = root_span.to_header()

    # 3. Assuming invoke another service, need to pass span header to another service for linking trace
    llm_runner.invoke_service_b(header)

    # 3. rootSpan finish
    root_span.finish()

    # 4. (optional) flush or close
    # -- force flush, report all traces in the queue
    # Warning! In general, this method is not needed to be call, as spans will be automatically reported in batches.
    # Note that flush will block and wait for the report to complete, and it may cause frequent reporting,
    # affecting performance.
    client.flush()

    # -- close trace, do flush and close client
    # Warning! Once Close is executed, the client will become unavailable and a new client needs
    # to be created via NewClient! Use it only when you need to release resources, such as shutting down an instance!
    # client.close(ctx)