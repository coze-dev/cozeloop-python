# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
import logging
import time
import threading

from cozeloop import set_log_level, new_client


class LLMRunner:
    def __init__(self, client):
        self.client = client

    def llm_call(self):
        """
        Simulate an LLM call and set relevant span tags.
        """
        input_data = 'test input'
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


set_log_level(logging.DEBUG)
client = new_client()
llm_runner = LLMRunner(client)

def worker(interval, stop_event):
    while not stop_event.is_set():
        start_time = time.time()

        threading.Thread(target=llm_runner.llm_call).start()

        elapsed_time = time.time() - start_time

        if elapsed_time < interval:
            time.sleep(interval - elapsed_time)


def benchmark(qps, duration):
    """
    qps: qps
    duration: test run time
    """
    interval = 1.0 / qps
    stop_event = threading.Event()


    control_thread = threading.Thread(target=worker, args=(interval, stop_event))
    control_thread.start()

    # run duration
    time.sleep(duration)

    stop_event.set()
    control_thread.join()


def test_trace_benchmark():
    benchmark(qps=500, duration=20)