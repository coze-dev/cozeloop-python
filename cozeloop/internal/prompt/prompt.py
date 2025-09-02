# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
from typing import Dict, Any, List, Optional
import pydantic

from jinja2 import BaseLoader, Undefined
from jinja2.sandbox import SandboxedEnvironment
from jinja2.utils import missing, object_type_repr

from cozeloop.entities.prompt import (Prompt, Message, VariableDef, VariableType, TemplateType, Role,
                                      PromptVariable, ContentPart, ContentType)
from cozeloop.internal import consts
from cozeloop.internal.consts.error import RemoteServiceError
from cozeloop.internal.httpclient.client import Client
from cozeloop.internal.prompt.cache import PromptCache
from cozeloop.internal.prompt.converter import _convert_prompt, _to_span_prompt_input, _to_span_prompt_output
from cozeloop.internal.prompt.openapi import OpenAPIClient, PromptQuery
from cozeloop.internal.trace.trace import TraceProvider
from cozeloop.spec.tracespec import PROMPT_KEY, INPUT, PROMPT_VERSION, V_SCENE_PROMPT_TEMPLATE, V_SCENE_PROMPT_HUB, PROMPT_LABEL


class PromptProvider:
    def __init__(
            self,
            workspace_id: str,
            http_client: Client,
            trace_provider: TraceProvider,
            prompt_cache_max_count: int = 100,
            prompt_cache_refresh_interval: int = 60,
            prompt_trace: bool = False
    ):
        self.workspace_id = workspace_id
        self.openapi_client = OpenAPIClient(http_client)
        self.trace_provider = trace_provider
        self.cache = PromptCache(workspace_id, self.openapi_client,
                                 refresh_interval=prompt_cache_refresh_interval,
                                 max_size=prompt_cache_max_count,
                                 auto_refresh=True)
        self.prompt_trace = prompt_trace

    def get_prompt(self, prompt_key: str, version: str = '', label: str = '') -> Optional[Prompt]:
        # Trace reporting
        if self.prompt_trace and self.trace_provider is not None:
            with self.trace_provider.start_span(consts.TRACE_PROMPT_HUB_SPAN_NAME,
                                                consts.TRACE_PROMPT_HUB_SPAN_TYPE,
                                                scene=V_SCENE_PROMPT_HUB) as prompt_hub_pan:
                prompt_hub_pan.set_tags({
                    PROMPT_KEY: prompt_key,
                    INPUT: json.dumps({PROMPT_KEY: prompt_key, PROMPT_VERSION: version, PROMPT_LABEL: label})
                })
                try:
                    prompt = self._get_prompt(prompt_key, version, label)
                    if prompt is not None:

                        output = None
                        if pydantic.VERSION.startswith('1'):
                            output = prompt.json()
                        else:
                            output = prompt.model_dump_json(exclude_none=True)
                        prompt_hub_pan.set_tags({
                            PROMPT_VERSION: prompt.version,
                            consts.OUTPUT: output,
                        })
                    return prompt
                except RemoteServiceError as e:
                    prompt_hub_pan.set_status_code(e.error_code)
                    prompt_hub_pan.set_error(e.error_message)
                    raise e
                except Exception as e:
                    prompt_hub_pan.set_error(str(e))
                    raise e
        else:
            return self._get_prompt(prompt_key, version, label)

    def _get_prompt(self, prompt_key: str, version: str, label: str = '') -> Optional[Prompt]:
        """
        Get Prompt, prioritize retrieving from cache, if not found then fetch from server
        """
        # Try to get from cache
        prompt = self.cache.get(prompt_key, version, label)
        # If not in cache, fetch from server and cache it
        if prompt is None:
            result = self.openapi_client.mpull_prompt(self.workspace_id, [PromptQuery(prompt_key=prompt_key, version=version, label=label)])
            if result:
                prompt = _convert_prompt(result[0].prompt)
                self.cache.set(prompt_key, version, label, prompt)
        # object cache item should be read only
        return prompt.copy(deep=True)

    def prompt_format(
            self,
            prompt: Prompt,
            variables: Dict[str, PromptVariable]
    ) -> List[Message]:
        if self.prompt_trace and self.trace_provider is not None:
            with self.trace_provider.start_span(consts.TRACE_PROMPT_TEMPLATE_SPAN_NAME,
                                                consts.TRACE_PROMPT_TEMPLATE_SPAN_TYPE,
                                                scene=V_SCENE_PROMPT_TEMPLATE) as prompt_template_span:
                input = None
                if pydantic.VERSION.startswith('1'):
                    input = _to_span_prompt_input(prompt.prompt_template.messages, variables).json()
                else:
                    input = _to_span_prompt_input(prompt.prompt_template.messages, variables).model_dump_json(exclude_none=True)
                prompt_template_span.set_tags({
                    PROMPT_KEY: prompt.prompt_key,
                    PROMPT_VERSION: prompt.version,
                    consts.INPUT: input
                })
                try:
                    results = self._prompt_format(prompt, variables)
                    output = None
                    if pydantic.VERSION.startswith('1'):
                        output = _to_span_prompt_output(results).json()
                    else:
                        output = _to_span_prompt_output(results).model_dump_json(exclude_none=True)
                    prompt_template_span.set_tags({
                        consts.OUTPUT: output,
                    })
                    return results
                except RemoteServiceError as e:
                    prompt_template_span.set_status_code(e.error_code)
                    prompt_template_span.set_error(e.error_message)
                    raise e
                except Exception as e:
                    prompt_template_span.set_error(str(e))
                    raise e
        else:
            return self._prompt_format(prompt, variables)

    def _prompt_format(
            self,
            prompt: Prompt,
            variables: Dict[str, PromptVariable]
    ) -> List[Message]:
        results = []
        if prompt.prompt_template is None or len(prompt.prompt_template.messages) == 0:
            return results

        # Validate variable types
        self._validate_variable_values_type(prompt.prompt_template.variable_defs, variables)

        # Process normal messages
        results = self._format_normal_messages(
            prompt.prompt_template.template_type,
            prompt.prompt_template.messages,
            prompt.prompt_template.variable_defs,
            variables
        )

        # Process placeholder messages
        results = self._format_placeholder_messages(results, variables)

        return results

    def _validate_variable_values_type(self, variable_defs: List[VariableDef], variables: Dict[str, PromptVariable]):
        if variable_defs is None:
            return
        for var_def in variable_defs:
            if var_def is None:
                continue

            val = variables.get(var_def.key)
            if val is None:
                continue

            if var_def.type == VariableType.STRING:
                if not isinstance(val, str):
                    raise ValueError(f"type of variable '{var_def.key}' should be string")
            elif var_def.type == VariableType.PLACEHOLDER:
                if not (isinstance(val, Message) or (isinstance(val, List) and all(isinstance(item, Message) for item in val))):
                    raise ValueError(f"type of variable '{var_def.key}' should be Message like object")
            elif var_def.type == VariableType.BOOLEAN:
                if not isinstance(val, bool):
                    raise ValueError(f"type of variable '{var_def.key}' should be bool")
            elif var_def.type == VariableType.INTEGER:
                if not isinstance(val, int):
                    raise ValueError(f"type of variable '{var_def.key}' should be int")
            elif var_def.type == VariableType.FLOAT:
                if not isinstance(val, float):
                    raise ValueError(f"type of variable '{var_def.key}' should be float")
            elif var_def.type == VariableType.ARRAY_STRING:
                if not isinstance(val, list) or not all(isinstance(item, str) for item in val):
                    raise ValueError(f"type of variable '{var_def.key}' should be array<string>")
            elif var_def.type == VariableType.ARRAY_BOOLEAN:
                if not isinstance(val, list) or not all(isinstance(item, bool) for item in val):
                    raise ValueError(f"type of variable '{var_def.key}' should be array<boolean>")
            elif var_def.type == VariableType.ARRAY_INTEGER:
                if not isinstance(val, list) or not all(isinstance(item, int) for item in val):
                    raise ValueError(f"type of variable '{var_def.key}' should be array<integer>")
            elif var_def.type == VariableType.ARRAY_FLOAT:
                if not isinstance(val, list) or not all(isinstance(item, float) for item in val):
                    raise ValueError(f"type of variable '{var_def.key}' should be array<float>")
            elif var_def.type == VariableType.MULTI_PART:
                if not isinstance(val, list) or not all(isinstance(item, ContentPart) for item in val):
                    raise ValueError(f"type of variable '{var_def.key}' should be multi_part")

    def _format_normal_messages(
            self,
            template_type: TemplateType,
            messages: List[Message],
            variable_defs: List[VariableDef],
            variables: Dict[str, PromptVariable]
    ) -> List[Message]:
        results = []
        variable_def_map = {var_def.key: var_def for var_def in variable_defs if var_def} if variable_defs else {}

        for message in messages:
            if message is None:
                continue

            # Placeholder messages will be processed later
            if message.role == Role.PLACEHOLDER:
                results.append(message)
                continue

            # Render content
            if message.content:
                rendered_content = self._render_text_content(
                    template_type,
                    message.content,
                    variable_def_map,
                    variables
                )
                message.content = rendered_content
            # Render parts
            if message.parts:
                message.parts = self.format_multi_part(
                    template_type,
                    message.parts,
                    variable_def_map,
                    variables
                )

            results.append(message)

        return results

    def format_multi_part(
            self,
            template_type: TemplateType,
            parts: List[Optional[ContentPart]],
            def_map: Dict[str, VariableDef],
            val_map: Dict[str, Any]) -> List[ContentPart]:
        formatted_parts: List[ContentPart] = []

        # Render text
        for part in parts:
            if part is None:
                continue
            if part.type == ContentType.TEXT and part.text is not None:
                rendered_text = self._render_text_content(
                    template_type, part.text, def_map, val_map
                )
                part.text = rendered_text

        # Render multi-part variable
        for part in parts:
            if part is None:
                continue
            if part.type == ContentType.MULTI_PART_VARIABLE and part.text is not None:
                multi_part_key = part.text
                if multi_part_key in def_map and multi_part_key in val_map:
                    vardef = def_map[multi_part_key]
                    value = val_map[multi_part_key]
                    if vardef is not None and value is not None and vardef.type == VariableType.MULTI_PART:
                            formatted_parts.extend(value)
            else:
                formatted_parts.append(part)

        # Filter
        filtered: List[ContentPart] = []
        for pt in formatted_parts:
            if pt is None:
                continue
            if pt.text is not None or pt.image_url is not None:
                filtered.append(pt)
        return filtered

    def _format_placeholder_messages(
            self,
            messages: List[Message],
            variables: Dict[str, PromptVariable]
    ) -> List[Message]:
        expanded_messages = []

        for message in messages:
            if message and message.role == Role.PLACEHOLDER:
                placeholder_var_name = message.content
                if placeholder_messages := variables.get(placeholder_var_name):
                    if isinstance(placeholder_messages, list):
                        expanded_messages.extend(placeholder_messages)
                    else:
                        expanded_messages.append(placeholder_messages)
            else:
                expanded_messages.append(message)

        return expanded_messages


    def _render_text_content(
            self,
            template_type: TemplateType,
            template_str: str,
            variable_def_map: Dict[str, VariableDef],
            variables: Dict[str, Any]
    ) -> str:
        if template_type == TemplateType.NORMAL:
            # Create custom Environment using DebugUndefined to preserve original form of undefined variables
            env = SandboxedEnvironment(
                loader=BaseLoader(),
                undefined=CustomUndefined,
                variable_start_string='{{',
                variable_end_string='}}',
                keep_trailing_newline=True
            )
            # Create template
            template = env.from_string(template_str)
            # Only pass variables defined in variable_def_map, replace undefined variables with empty string
            render_vars = {k: variables.get(k, '') for k in variable_def_map.keys()}
            # Render template
            return template.render(**render_vars)
        elif template_type == TemplateType.JINJA2:
            return self._render_jinja2_template(template_str, variable_def_map, variables)
        else:
            raise ValueError(f"text render unsupported template type: {template_type}")


    def _render_jinja2_template(self, template_str: str, variable_def_map: Dict[str, VariableDef],
                                variables: Dict[str, Any]) -> str:
        """渲染 Jinja2 模板"""
        env = SandboxedEnvironment()
        template = env.from_string(template_str)
        render_vars = {k: variables[k] for k in variable_def_map.keys() if variables is not None and k in variables}
        return template.render(**render_vars)

class CustomUndefined(Undefined):
    __slots__ = ()

    def __str__(self) -> str:
        if self._undefined_hint:
            message = f"undefined value printed: {self._undefined_hint}"

        elif self._undefined_obj is missing:
            message = self._undefined_name  # type: ignore

        else:
            message = (
                f"no such element: {object_type_repr(self._undefined_obj)}"
                f"[{self._undefined_name!r}]"
            )

        return f"{{{{{message}}}}}"

