# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
import os
import time
from typing import List

import cozeloop
from cozeloop import Message
from cozeloop.entities.prompt import Role
from cozeloop.spec.tracespec import CALL_OPTIONS, ModelCallOption, ModelMessage, ModelInput


def convert_model_input(messages: List[Message]) -> ModelInput:
    model_messages = []
    for message in messages:
        model_messages.append(ModelMessage(
            role=str(message.role),
            content=message.content if message.content is not None else ""
        ))

    return ModelInput(
        messages=model_messages
    )


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
            span.set_input(convert_model_input(input_data))
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
            span.set_tags({CALL_OPTIONS: ModelCallOption(
                temperature=0.5,
                top_p=0.5,
                top_k=10,
                presence_penalty=0.5,
                frequency_penalty=0.5,
                max_tokens=1024,
            )})

            return None
        except Exception as e:
            raise e
        finally:
            span.finish()

# If you have some advanced usages, such as using jinja templates in prompts, you can refer to the following.
if __name__ == '__main__':
    # 1.Create a prompt on the platform
    # You can create a Prompt on the platform's Prompt development page (set Prompt Key to 'prompt_hub_demo'),
    # add the following messages to the template, and submit a version.
    # System: You are a helpful bot, the conversation topic is {{var1}}.
    # Placeholder: placeholder1
    # User: My question is {{var2}}
    # Placeholder: placeholder2

    # Set the following environment variables first.
    # COZELOOP_WORKSPACE_ID=your workspace id
    # COZELOOP_API_TOKEN=your token
    # 2.New loop client
    client = cozeloop.new_client(
        # Set whether to report a trace span when get or format prompt.
        # Default value is false.
        prompt_trace=True,
        workspace_id="7496795200791511052",
        api_token="pat_tClAonoIB5ET9fVFLr75o1rHxoxaaxPaodLyIOeL5CLy8XLlpTuxkEdrDOXSCxky")

    os.environ["x-tt-env"] = "ppe_wf_loop_pe"
    os.environ["x-use-ppe"] = "1"

    # 3. new root span
    rootSpan = client.start_span("root_span", "main_span")

    # 4. Get the prompt
    # If no specific version is specified, the latest version of the corresponding prompt will be obtained
    prompt = client.get_prompt(prompt_key="wf1", version="0.0.3")
    if prompt is not None:
        # Get messages of the prompt
        if prompt.prompt_template is not None:
            messages = prompt.prompt_template.messages
            print(
                f"prompt messages: {json.dumps([message.model_dump(exclude_none=True) for message in messages], ensure_ascii=False)}")
        # Get llm config of the prompt
        if prompt.llm_config is not None:
            llm_config = prompt.llm_config
            print(f"prompt llm_config: {llm_config.model_dump_json(exclude_none=True)}")

        # 5.Format messages of the prompt
        formatted_messages = client.prompt_format(prompt, {
            "var_string": "hi",
            "var_int": 5,
            "var_bool": True,
            "var_float": 1.0,
            "var_object": {
                "name":    "John",
                "age":     30,
                "hobbies": ["reading", "coding"],
                "address": {
                    "city":   "bejing",
                    "street": "123 Main",
                },
            },
            "var_array_string": ["hello", "nihao"],
            "var_array_boolean": [True, False, True],
            "var_array_int": [1, 2, 3, 4],
            "var_array_float": [1.0, 2.0],
            "var_array_object": [{"key": "123"}, {"value": 100}],
            # Placeholder variable type should be Message/List[Message]
            "placeholder1": [Message(role=Role.USER, content="Hello!"),
                             Message(role=Role.ASSISTANT, content="Hello!")]
            # Other variables in the prompt template that are not provided with corresponding values will be
            # considered as empty values.
        })
        print(
            f"formatted_messages: {json.dumps([message.model_dump(exclude_none=True) for message in formatted_messages], ensure_ascii=False)}")

        # 6.LLM call
        llm_runner = LLMRunner(client)
        llm_runner.llm_call(formatted_messages)

    rootSpan.finish()
    # 4. (optional) flush or close
    # -- force flush, report all traces in the queue
    # Warning! In general, this method is not needed to be call, as spans will be automatically reported in batches.
    # Note that flush will block and wait for the report to complete, and it may cause frequent reporting,
    # affecting performance.
    client.flush()
