# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import time
import threading

from cozeloop import new_client
from cozeloop.logger import set_log_level

logger = logging.getLogger(__name__)


# Define error code constant
ERR_CODE_LLM_CALL = 600789111


class LLMRunner:
    def __init__(self, client):
        self.client = client

    def llm_call(self, input_data):
        """
        modelSpan is child of rootSpan by ctx
        """
        model_span = self.client.start_span("llmCall", "model")
        try:
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
            model_span.set_output( output)
            # set tag key: `model_provider`, e.g., openai, etc.
            model_span.set_model_provider( "openai")
            # set tag key: `start_time_first_resp`
            # Timestamp of the first packet return from LLM, unit: microseconds.
            # When `start_time_first_resp` is set, a tag named `latency_first_resp` calculated
            # based on the modelSpan's StartTime will be added, meaning the latency for the first packet.
            model_span.set_start_time_first_resp( int(time.time() * 1000000))
            # set tag key: `input_tokens`. The amount of input tokens.
            # when the `input_tokens` value is set, it will automatically sum with the `output_tokens` to calculate the `tokens` tag.
            model_span.set_input_tokens( input_token)
            # set tag key: `output_tokens`. The amount of output tokens.
            # when the `output_tokens` value is set, it will automatically sum with the `input_tokens` to calculate the `tokens` tag.
            model_span.set_output_tokens( output_token)
            # set tag key: `model_name`, e.g., gpt-4-1106-preview, etc.
            model_span.set_model_name( "gpt-4-1106-preview")

            return None
        except Exception as err:
            return err
        finally:
            model_span.finish()

    def async_rending(self, span_context):
        """
        asynSpan is child of rootSpan by WithChildOf
        """
        asyn_span = self.client.start_span("asynRending", "rending", child_of=span_context)
        try:
            # Assuming asynRending is processing
            time.sleep(1)
            asyn_span.set_status_code(0)
        finally:
            asyn_span.finish()


def main():
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # COZELOOP_WORKSPACE_ID=your workspace id
    # COZELOOP_API_TOKEN=your token

    # 0. new client rootSpan
    set_log_level(logging.INFO)
    client = new_client()
    llm_runner = LLMRunner(client)

    # 1. start rootSpan, because there is no rootSpan in the  so parentSpan is root rootSpan of new trace
    root_span = client.start_span("root_span", "main_span")

    # 2. rootSpan set tag or baggage
    # set custom tag
    root_span.set_tags({
        "service_name": "core",
    })

    # set custom baggage, baggage can cover tag of sample key, and baggage will pass to child rootSpan automatically.
    root_span.set_baggage({
        "product_id": "123456654321",  # Assuming product_id is global field, need to be passed to child rootSpan automatically.
        "product_name": "AI bot",  # Assuming product_name is global field, need to be passed to child rootSpan automatically.
        "product_version": "0.0.1",  # Assuming product_version is global field, need to be passed to child rootSpan automatically.
    })
    # set baggage key: `user_id`, implicitly set tag key: `user_id`
    root_span.set_user_id_baggage("123456")

    # assuming call llm
    if err := llm_runner.llm_call("What's your name?"):
        # set tag key: `_status_code`
        root_span.set_status_code(ERR_CODE_LLM_CALL)
        # set tag key: `error`, if `_status_code` value is not defined, `_status_code` value will be set -1.
        root_span.set_error(str(err))
        return

    # 3. Assuming need run an async task, and it's span is child span of rootSpan
    threading.Thread(target=llm_runner.async_rending, args=(root_span,)).start()

    # 4. rootSpan finish
    root_span.finish()

    # 5. (optional) flush or close
    # -- force flush, report all traces in the queue
    # Warning! In general, this method is not needed to be call, as spans will be automatically reported in batches.
    # Note that flush will block and wait for the report to complete, and it may cause frequent reporting,
    # affecting performance.
    client.flush()

    # Since asyncRending runs in a separate thread, its finish method may be executed later. Here we intentionally
    # add a delay to simulate the continuous operation of the service. In a real service, this delay is not required.
    time.sleep(5)

    # -- close trace, do flush and close client
    # Warning! Once Close is executed, the client will become unavailable and a new client needs
    # to be created via NewClient! Use it only when you need to release resources, such as shutting down an instance!
    # client.close()


if __name__ == "__main__":
    main()