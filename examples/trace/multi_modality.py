# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import base64
import logging
import time
import requests

from typing import Any

from cozeloop import new_client
from cozeloop.spec.tracespec import ModelInput, ModelMessage, ModelMessagePart, ModelMessagePartType, ModelImageURL, ModelFileURL
from cozeloop.logger import set_log_level

logger = logging.getLogger(__name__)


class LLMRunner:
    def __init__(self, client):
        self.client = client

    def llm_call(self,  input_data: Any):
        with self.client.start_span( "llmCall", "model") as span:
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
            span.set_start_time_first_resp(int(time.time() * 1000000))
            # set tag key: `input_tokens`
            span.set_input_tokens(input_token)
            # set tag key: `output_tokens`
            span.set_output_tokens(output_token)
            # set tag key: `model_name`, e.g., gpt-4-1106-preview, etc.
            span.set_model_name("gpt-4-1106-preview")


def get_mdn_base64(url: str) -> str:
    resp = requests.get(url)
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch image: status code {resp.status_code}")

    mime_type = resp.headers['Content-Type']
    base64_data = base64.b64encode(resp.content).decode('utf-8')
    return f"data:{mime_type};base64,{base64_data}"

def get_multi_modality_input() -> ModelInput:
    image_base64_str = get_mdn_base64("https://www.w3schools.com/w3images/lights.jpg")
    file_base64_str = get_mdn_base64("https://docs.python.org/3.13/archives/python-3.13-docs-pdf-a4.zip")

    return ModelInput(
        messages=[
            ModelMessage(
                parts=[
                    ModelMessagePart(
                        type=ModelMessagePartType.TEXT,
                        text="test txt",
                    ),
                    ModelMessagePart(
                        type=ModelMessagePartType.IMAGE,
                        image_url=ModelImageURL(
                            name="test image url",
                            url="https://www.w3schools.com/w3images/lights.jpg",
                        ),
                    ),
                    ModelMessagePart(
                        type=ModelMessagePartType.IMAGE,
                        image_url=ModelImageURL(
                            name="test image binary",
                            url=image_base64_str,
                        ),
                    ),
                    ModelMessagePart(
                        type=ModelMessagePartType.FILE,
                        file_url=ModelFileURL(
                            name="test file url",
                            url="https://docs.python.org/3.13/archives/python-3.13-docs-pdf-a4.zip",
                            suffix="zip",
                        ),
                    ),
                    ModelMessagePart(
                        type=ModelMessagePartType.FILE,
                        file_url=ModelFileURL(
                            name="test file binary",
                            url=file_base64_str,
                            suffix="zip",
                        ),
                    ),
                ]
            )
        ]
    )

def main():
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # COZELOOP_WORKSPACE_ID=your workspace id
    # COZELOOP_API_TOKEN=your token

    # 0. new client span
    set_log_level(logging.INFO)
    client = new_client()
    llm_runner = LLMRunner(client)

    # 1. start span
    with client.start_span("root_span", "main_span") as span:
        # 2. span set tag or baggage
        # set custom tag
        span.set_tags({
            "mode": "multi_modality",
            "node_id": 6076665,
            "node_process_duration": 228.6
        })

        # set custom baggage
        span.set_baggage({
            "product_id": "123456654321"
        })
        # set baggage key: `user_id`, implicitly set tag key: `user_id`
        span.set_user_id_baggage("123456")

        # assuming call llm
        try:
            input_data = get_multi_modality_input()
            llm_runner.llm_call(input_data)
        except Exception as e:
            # set tag key: `_status_code`
            span.set_status_code(600789112)
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