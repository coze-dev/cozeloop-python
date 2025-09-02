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
    """将 cozeloop Message 转换为 ModelInput"""
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
    """LLM 运行器，用于模拟 LLM 调用并设置相关的 span 标签"""
    
    def __init__(self, client):
        self.client = client

    def llm_call(self, input_data):
        """
        模拟 LLM 调用并设置相关的 span 标签
        """
        span = self.client.start_span("llmCall", "model")
        try:
            # 模拟 LLM 处理过程
            # output = ChatOpenAI().invoke(input=input_data)

            # 模拟响应
            time.sleep(1)
            output = "I'm a robot. I don't have a specific name. You can give me one."
            input_token = 232
            output_token = 1211

            # 设置 span 标签
            span.set_input(convert_model_input(input_data))
            span.set_output(output)
            span.set_model_provider("openai")
            span.set_start_time_first_resp(int(time.time() * 1000000))
            span.set_input_tokens(input_token)
            span.set_output_tokens(output_token)
            span.set_model_name("gpt-4-1106-preview")
            span.set_tags({CALL_OPTIONS: ModelCallOption(
                temperature=0.5,
                top_p=0.5,
                top_k=10,
                presence_penalty=0.5,
                frequency_penalty=0.5,
                max_tokens=1024,
            )})

            return output
        except Exception as e:
            raise e
        finally:
            span.finish()


if __name__ == '__main__':
    # 1.Create a prompt on the platform
    # You can create a Prompt on the platform's Prompt development page (set Prompt Key to 'prompt_hub_label_demo'),
    # add the following messages to the template, and submit a version with label.
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
        prompt_trace=True)

    try:
        # 3. Get the prompt by prompt_key and label
        # Note: When version is specified, label will be ignored.
        prompt = client.get_prompt(prompt_key="prompt_hub_label_demo", label="production")
        if prompt is not None:
            print(f"Got prompt by label: {prompt.prompt_key}")
            
            # Get messages of the prompt
            if prompt.prompt_template is not None:
                messages = prompt.prompt_template.messages
                print(
                    f"prompt messages: {json.dumps([message.model_dump(exclude_none=True) for message in messages], ensure_ascii=False)}")
            
            # Get llm config of the prompt
            if prompt.llm_config is not None:
                llm_config = prompt.llm_config
                print(f"prompt llm_config: {llm_config.model_dump_json(exclude_none=True)}")

            # 4.Format messages of the prompt
            formatted_messages = client.prompt_format(prompt, {
                # Normal variable type should be string
                "var1": "artificial intelligence",
                "var2": "What is the weather like?",
                # Placeholder variable type should be Message/List[Message]
                "placeholder1": [Message(role=Role.USER, content="Hello!"),
                                 Message(role=Role.ASSISTANT, content="Hello!")],
                "placeholder2": [Message(role=Role.USER, content="Nice to meet you!")]
                # Other variables in the prompt template that are not provided with corresponding values will be
                # considered as empty values.
            })
            print(
                f"formatted_messages: {json.dumps([message.model_dump(exclude_none=True) for message in formatted_messages], ensure_ascii=False)}")
            
            # 5. Use LLM Runner to call LLM with formatted messages
            llm_runner = LLMRunner(client)
            result = llm_runner.llm_call(formatted_messages)
            print(f"LLM response: {result}")
            
        else:
            print("Prompt not found with the specified label")

    finally:
        # 6. (optional) flush or close
        # -- force flush, report all traces in the queue
        # Warning! In general, this method is not needed to be call, as spans will be automatically reported in batches.
        # Note that flush will block and wait for the report to complete, and it may cause frequent reporting,
        # affecting performance.
        client.flush()
