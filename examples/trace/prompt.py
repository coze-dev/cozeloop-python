# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT
import logging
from typing import Optional, List, Dict, Any
import json

from cozeloop.internal.consts import TRACE_PROMPT_HUB_SPAN_NAME, TRACE_PROMPT_TEMPLATE_SPAN_NAME
from cozeloop.entities.prompt import PromptTemplate, Prompt, Message, Role
from cozeloop import new_client, set_log_level
from cozeloop.spec.tracespec import ModelMessage, PromptInput, PromptArgument, V_PROMPT_HUB_SPAN_TYPE, PROMPT_KEY, \
    INPUT, PROMPT_VERSION, OUTPUT, V_PROMPT_SPAN_TYPE


class LLMRunner:
    def __init__(self, client):
        self.client = client


ERR_CODE_INTERNAL = 600789111


def main():
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # COZELOOP_WORKSPACE_ID=your workspace id
    # COZELOOP_API_TOKEN=your token

    set_log_level(logging.INFO)
    client = new_client()

    get_prompt_runner = GetPromptRunner(client=client)

    # 1. start span
    span = client.start_span( "root_span", "main_span")

    # 2. set span tag and baggage
    span.set_tags({
        "mode": "simple",
        "node_id": 6076665,
        "node_process_duration": 228.6
    })

    span.set_baggage({
        "product_id": "123456654321"
    })
    span.set_user_id_baggage("123456")

    # assuming call llm
    prompt, err = get_prompt_runner.get_prompt()
    if err:
        span.set_status_code(ERR_CODE_INTERNAL)
        span.set_error(str(err))

    res_prompt = get_prompt_runner.format_prompt(prompt, {"var1": "What skills do you have?"})

    # 3. finish span
    span.finish()

    # 5. (optional) flush or close
    # -- force flush, report all traces in the queue
    # Warning! In general, this method is not needed to be call, as spans will be automatically reported in batches.
    # Note that flush will block and wait for the report to complete, and it may cause frequent reporting,
    # affecting performance.
    client.flush()


def get_prompt() -> [Optional[Prompt]]:
    return Prompt(
        prompt_template=PromptTemplate(
            messages=[
                Message(role=Role.SYSTEM, content="Hello!"),
                Message(role=Role.USER, content="Hello! {{var1}}")
            ]
        )
    )


def do_prompt_format() -> List[Message]:
    return []  # mock


def to_span_prompt_input(messages: List[Message], arguments: Dict[str, Any]) -> PromptInput:
    return PromptInput(
        templates=to_span_messages(messages),
        arguments=to_span_arguments(arguments)
    )


def to_span_arguments(arguments: Dict[str, Any]) -> List[PromptArgument]:
    return [
        PromptArgument(key=key, value=value)
        for key, value in arguments.items()
    ]


def to_span_messages(messages: List[Message]) -> List[ModelMessage]:
    return [to_span_message(msg) for msg in messages]


def to_span_message(message: Optional[Message]) -> Optional[ModelMessage]:
    if not message:
        return None
    return ModelMessage(
        role=str(message.role),
        content=message.content if message.content else ""
    )


class GetPromptRunner:
    def __init__(self, client):
        self.client = client

    def get_prompt(self) -> Optional[Prompt]:
        span = self.client.start_span("get_prompt", V_PROMPT_HUB_SPAN_TYPE, None)
        try:
            prompt_hub_span = self.client.start_span(TRACE_PROMPT_HUB_SPAN_NAME,
                                                          V_PROMPT_HUB_SPAN_TYPE)
            try:
                prompt = get_prompt()

                if prompt_hub_span:
                    prompt_hub_span.set_tags({
                        PROMPT_KEY: "test_demo",
                        INPUT: json.dumps({
                            PROMPT_KEY: "test_demo",
                            PROMPT_VERSION: "v1.0.1"
                        }),
                        PROMPT_VERSION: "v1.0.1",  # mock version
                        OUTPUT: prompt
                    })

                return prompt
            finally:
                if prompt_hub_span:
                    prompt_hub_span.finish()
        finally:
            span.finish()

    def format_prompt(self, prompt: Prompt, variables: Dict[str, Any]) -> List[Message]:
        span = self.client.start_span("format_prompt", V_PROMPT_SPAN_TYPE, None)
        try:
            prompt_template_span = self.client.start_span(TRACE_PROMPT_TEMPLATE_SPAN_NAME,
                                                               V_PROMPT_SPAN_TYPE)
            try:
                messages, err = do_prompt_format()

                if prompt_template_span:
                    prompt_template_span.set_tags({
                        PROMPT_KEY: "test_demo",
                        PROMPT_VERSION: "v1.0.1",
                        INPUT: json.dumps(to_span_prompt_input(prompt.prompt_template.messages, variables)),
                        OUTPUT: json.dumps(to_span_messages(messages))
                    })
                    if err:
                        prompt_template_span.set_error(str(err))

                return messages, err
            finally:
                if prompt_template_span:
                    prompt_template_span.finish()
        finally:
            span.finish()