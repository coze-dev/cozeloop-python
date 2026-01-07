# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from __future__ import annotations
import json
import threading
import time
import traceback
from typing import List, Dict, Union, Any, Optional, Callable, Protocol

import pydantic
from pydantic import Field, BaseModel
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult, ChatGeneration
from langchain_core.agents import AgentFinish, AgentAction
from langchain_core.prompt_values import PromptValue, ChatPromptValue
from langchain_core.messages import BaseMessage, AIMessageChunk, AIMessage
from langchain_core.prompts import AIMessagePromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.outputs import ChatGenerationChunk, GenerationChunk

from cozeloop import Span, Client
from cozeloop._client import get_default_client
from cozeloop.integration.langchain.trace_model.llm_model import ModelTraceInput, ModelMeta, ModelTraceOutput, Message
from cozeloop.integration.langchain.trace_model.prompt_template import PromptTraceOutput, Argument, PromptTraceInput
from cozeloop.integration.langchain.trace_model.runtime import RuntimeInfo
from cozeloop.integration.langchain.util import calc_token_usage, get_prompt_tag


class LoopTracer:
    @classmethod
    def get_callback_handler(
            cls,
            client: Client = None,
            modify_name_fn: Optional[Callable[[str], str]] = None,
            add_tags_fn: Optional[Callable[[str], Dict[str, Any]]] = None,
            tags: Dict[str, Any] = None,
            child_of: Optional[Span] = None,
            state_span_ctx_key: str = None,
    ):
        """
        Do not hold it for a long time, get a new callback_handler for each request.
        client:             cozeloop client instance. If not provided, use the default client.
        modify_name_fn:     modify name function, input is node name(if you use langgraph, like add_node(node_name, node_func), it is node name), output is span name.
        add_tags_fn:        add tags function, input is node name(if you use langgraph, like add_node(node_name, node_func), it is node name), output is tags dict.
                            It's priority higher than parameter tags.
        tags:               default tags dict. It's priority lower than parameter add_tags_fn.
        child_of:           parent span of this callback_handler.
        state_span_ctx_key: span context field name in state. If provided, you need set the field in sate, and we will use it to set span context in state.
                            You can get it from state for creating inner span in async node.
        """
        return LoopTraceCallbackHandler(
            name_fn=modify_name_fn,
            tags_fn=add_tags_fn,
            tags=tags,
            child_of=child_of,
            client=client,
            state_span_ctx_key=state_span_ctx_key,
        )


class LoopTraceCallbackHandler(BaseCallbackHandler):
    def __init__(
            self,
            name_fn: Optional[Callable[[str], str]] = None,
            tags_fn: Optional[Callable[[str], Dict[str, Any]]] = None,
            tags: Dict[str, Any] = None,
            child_of: Optional[Span] = None,
            client: Client = None,
            state_span_ctx_key: str = None,
    ):
        super().__init__()
        self._client = client if client else get_default_client()
        self._space_id = self._client.workspace_id
        self.run_map: Dict[str, Run] = {}
        self.name_fn = name_fn
        self.tags_fn = tags_fn
        self._tags = tags if tags else {}
        self.trace_id: Optional[str] = None
        self.root_span_id: Optional[str] = None
        self._id_lock = threading.Lock()
        self._child_of = child_of
        self._state_span_ctx_key = state_span_ctx_key

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> Any:
        span_tags = {}
        span_name = serialized.get('name', 'unknown')

        flow_span = self._new_flow_span(span_name, 'model', **kwargs)
        try:
            span_tags['input'] = ModelTraceInput([BaseMessage(type='', content=prompt) for prompt in prompts],
                                                 kwargs.get('invocation_params', {})).to_json()
        except Exception as e:
            span_tags['internal_error'] = repr(e)
            span_tags['internal_error_trace'] = traceback.format_exc()
        finally:
            span_tags.update(_get_model_span_tags(**kwargs))
            self._set_span_tags(flow_span, span_tags)
            #  Store some pre-aspect information.
            self.run_map[str(kwargs['run_id'])].model_meta = ModelMeta(
                message=[{'role': '', 'content': prompt} for prompt in prompts],
                model_name=span_tags.get('model_name', ''))
        return flow_span

    def on_chat_model_start(self, serialized: Dict[str, Any], messages: List[List[BaseMessage]], **kwargs: Any) -> Any:
        span_tags = {}
        span_name = serialized.get('name', 'unknown')

        flow_span = self._new_flow_span(span_name, 'model', **kwargs)
        try:
            span_tags['input'] = ModelTraceInput(messages, kwargs.get('invocation_params', {})).to_json()
        except Exception as e:
            span_tags['internal_error'] = repr(e)
            span_tags['internal_error_trace'] = traceback.format_exc()
        finally:
            span_tags.update(_get_model_span_tags(**kwargs))
            self._set_span_tags(flow_span, span_tags)
            #  Store some pre-aspect information.
            self.run_map[str(kwargs['run_id'])].model_meta = (
                ModelMeta(message=[{'role': message.type, 'content': message.content} for inner_messages in messages for
                                   message in inner_messages], model_name=span_tags.get('model_name', '')))
        return flow_span

    async def on_llm_new_token(self, token: str, *, chunk: Optional[Union[GenerationChunk, ChatGenerationChunk]] = None,
                               **kwargs: Any) -> None:
        run_info = self.run_map.get(str(kwargs['run_id']), None)
        if run_info is None or run_info.model_meta is None or run_info.model_meta.receive_first_token:
            return
        first_token_latency = int(round(time.time() * 1000)) - run_info.model_meta.entry_timestamp
        run_info.model_meta.receive_first_token = True
        flow_span = self._get_flow_span(**kwargs)
        flow_span.set_tags({'latency_first_resp': first_token_latency})

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        flow_span = self._get_flow_span(**kwargs)
        try:
            # set output span_tag
            flow_span.set_tags({'output': ModelTraceOutput(response.generations).to_json()})
            # set model tags
            tags = self._get_model_tags(response, **kwargs)
            if tags:
                self._set_span_tags(flow_span, tags, need_convert_tag_value=False)
        except Exception as e:
            span_tags = {"internal_error": repr(e), 'internal_error_trace': traceback.format_exc()}
            self._set_span_tags(flow_span, span_tags, need_convert_tag_value=False)
        # finish flow_span
        self._end_flow_span(flow_span)

    def on_llm_error(self, error: Exception, **kwargs: Any) -> Any:
        self.on_chain_error(error, **kwargs)

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> Any:
        flow_span = None
        try:
            if kwargs.get('run_type', '') == 'prompt' or kwargs.get('name', '') == 'ChatPromptTemplate':
                flow_span = self._new_flow_span(kwargs['name'], 'prompt', **kwargs)
                self._on_prompt_start(flow_span, serialized, inputs, **kwargs)
            else:
                span_type = 'chain'
                if kwargs[
                    'name'] == 'LangGraph':  # LangGraph is Graph span_type，for trajectory evaluation aggregate to an agent
                    span_type = 'graph'
                flow_span = self._new_flow_span(kwargs['name'], span_type, **kwargs)
                flow_span.set_tags({'input': _convert_2_json(inputs)})
        except Exception as e:
            if flow_span is not None:
                span_tags = {"internal_error": repr(e), 'internal_error_trace': traceback.format_exc()}
                self._set_span_tags(flow_span, span_tags, need_convert_tag_value=False)
        finally:
            if flow_span is not None:
                # set trace_id
                with self._id_lock:
                    if hasattr(flow_span, 'context'):
                        self.trace_id = flow_span.context.trace_id
                    else:
                        self.trace_id = flow_span.trace_id
                # set span_ctx in state
                if self._state_span_ctx_key:
                    inputs[self._state_span_ctx_key] = flow_span
        return flow_span

    def on_chain_end(self, outputs: Union[Dict[str, Any], Any], **kwargs: Any) -> Any:
        flow_span = self.run_map[str(kwargs['run_id'])].span
        try:
            if self.run_map[str(kwargs['run_id'])].span_type == 'prompt' and isinstance(outputs, ChatPromptValue):
                messages: List[Message] = []
                for message in outputs.messages:
                    messages.append(Message(role=message.type, content=message.content))
                trace_output = PromptTraceOutput(prompts=messages)
                flow_span.set_tags({'output': trace_output.to_json()})
            else:
                flow_span.set_tags({'output': _convert_2_json(outputs)})
        except Exception as e:
            if flow_span:
                span_tags = {"internal_error": repr(e), 'internal_error_trace': traceback.format_exc()}
                self._set_span_tags(flow_span, span_tags, need_convert_tag_value=False)
        self._end_flow_span(flow_span)

    def on_chain_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> Any:
        flow_span = self._get_flow_span(**kwargs)
        if flow_span is None:
            span_name = '_Exception' if isinstance(error, Exception) else '_KeyboardInterrupt'
            flow_span = self._new_flow_span(span_name, 'chain_error', **kwargs)
        flow_span.set_tags({'error': repr(error), 'error_trace': traceback.format_exc()})
        self._end_flow_span(flow_span)

    def on_tool_start(
            self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> Any:
        span_tags = {'input': input_str, **serialized}
        span_name = serialized.get('name', 'unknown')
        flow_span = self._new_flow_span(span_name, 'tool', **kwargs)
        self._set_span_tags(flow_span, span_tags)
        return flow_span

    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        flow_span = self._get_flow_span(**kwargs)
        try:
            flow_span.set_tags({'output': _convert_2_json(output)})
        except Exception as e:
            span_tags = {"internal_error": repr(e), 'internal_error_trace': traceback.format_exc()}
            self._set_span_tags(flow_span, span_tags, need_convert_tag_value=False)
        self._end_flow_span(flow_span)

    def on_tool_error(
            self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> Any:
        flow_span = self._get_flow_span(**kwargs)
        if flow_span is None:
            span_name = '_Exception' if isinstance(error, Exception) else '_KeyboardInterrupt'
            flow_span = self._new_flow_span(span_name, 'tool_error', **kwargs)
        span_tags = {'error': repr(error), 'error_trace': traceback.format_exc()}
        self._set_span_tags(flow_span, span_tags, need_convert_tag_value=False)
        self._end_flow_span(flow_span)

    def on_text(self, text: str, **kwargs: Any) -> Any:
        """Run on arbitrary text."""

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        return

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> Any:
        return

    def _end_flow_span(self, span: Span):
        if span:
            span.finish()

    def _get_model_tags(self, response: LLMResult, **kwargs: Any) -> Dict[str, Any]:
        return self._get_model_token_tags(response, **kwargs)

    def _get_model_token_tags(self, response: LLMResult, **kwargs: Any) -> Dict[str, Any]:
        result = {}
        is_get_from_langchain = False
        if response.llm_output is not None and 'token_usage' in response.llm_output and response.llm_output[
            'token_usage']:
            is_get_from_langchain = True
            result['input_tokens'] = response.llm_output.get('token_usage', {}).get('prompt_tokens', 0)
            result['output_tokens'] = response.llm_output.get('token_usage', {}).get('completion_tokens', 0)
            result['tokens'] = result['input_tokens'] + result['output_tokens']
            reasoning_tokens = response.llm_output.get('token_usage', {}).get('completion_tokens_details', {}).get(
                'reasoning_tokens', 0)
            if reasoning_tokens:
                result['reasoning_tokens'] = reasoning_tokens
            input_cached_tokens = response.llm_output.get('token_usage', {}).get('prompt_tokens_details', {}).get(
                'cached_tokens', 0)
            if input_cached_tokens:
                result['input_cached_tokens'] = input_cached_tokens
        elif response.generations is not None and len(response.generations) > 0 and response.generations[0] is not None:
            for i, generation in enumerate(response.generations[0]):
                if isinstance(generation, ChatGeneration) and isinstance(generation.message, (
                        AIMessageChunk, AIMessage)) and generation.message.usage_metadata:
                    is_get_from_langchain = True
                    result['input_tokens'] = generation.message.usage_metadata.get('input_tokens', 0)
                    result['output_tokens'] = generation.message.usage_metadata.get('output_tokens', 0)
                    result['tokens'] = result['input_tokens'] + result['output_tokens']
                    if generation.message.usage_metadata.get('output_token_details', {}):
                        reasoning_tokens = generation.message.usage_metadata.get('output_token_details', {}).get(
                            'reasoning', 0)
                        if reasoning_tokens:
                            result['reasoning_tokens'] = reasoning_tokens
                    if generation.message.usage_metadata.get('input_token_details', {}):
                        input_read_cached_tokens = generation.message.usage_metadata.get('input_token_details', {}).get(
                            'cache_read', 0)
                        if input_read_cached_tokens:
                            result['input_cached_tokens'] = input_read_cached_tokens
                        input_creation_cached_tokens = generation.message.usage_metadata.get('input_token_details',
                                                                                             {}).get('cache_creation',
                                                                                                     0)
                        if input_creation_cached_tokens:
                            result['input_creation_cached_tokens'] = input_creation_cached_tokens
        if is_get_from_langchain:
            return result
        else:
            try:
                run_info = self.run_map[str(kwargs['run_id'])]
                if run_info is not None and run_info.model_meta is not None:
                    model_name = run_info.model_meta.model_name
                    input_messages = run_info.model_meta.message
                    token_usage = {
                        'input_tokens': calc_token_usage(input_messages, model_name),
                        'output_tokens': calc_token_usage(response, model_name),
                        'tokens': 0
                    }
                    token_usage['tokens'] = token_usage['input_tokens'] + token_usage['output_tokens']
                    return token_usage
            except Exception as e:
                span_tags = {'error_info': repr(e), 'error_trace': traceback.format_exc()}
                return span_tags

    def _on_prompt_start(self, flow_span, serialized: Dict[str, Any], inputs: (Dict[str, Any], str),
                         **kwargs: Any) -> None:
        # get inputs
        params: List[Argument] = []
        if isinstance(inputs, str):
            key = serialized['kwargs']['input_variables'][0]
            params.append(Argument(key=key, value=inputs))
        elif isinstance(inputs, dict):
            for key, val in inputs.items():
                if val is not None:
                    params.append(Argument(key=key, value=val))
        # get partial_inputs
        for key, val in serialized.get('kwargs', {}).get('partial_variables', {}).items():
            if val is not None:
                params.append(Argument(key=key, value=val, source='partial'))
        # get prompt_template
        messages: List[Message] = []
        messages_json = _get_value_from_json(serialized, 'messages')
        if messages_json is not None:
            for message_json in messages_json:
                class_name = _get_value_from_json(message_json, 'id')[3]
                role = _lc_prompt_role_converter(class_name)
                content = _get_value_from_json(message_json, 'template')
                if content is None:
                    content = _get_value_from_json(message_json, 'variable_name')
                messages.append(Message(role=role, content=content))
        else:
            template = _get_value_from_json(serialized, 'template')
            if template is not None:
                messages.append(Message(role='human', content=template))
        trace_input = PromptTraceInput(arguments=params,
                                       partial_inputs=serialized.get('kwargs', {}).get('partial_variables', {}),
                                       templates=messages)
        flow_span.set_tags({'input': trace_input.to_json()})
        # set prompt_key、prompt_version、prompt_provider span_tag
        prompt_key = get_prompt_tag(kwargs.get('tags', []))
        if len(prompt_key) == 2:
            flow_span.set_tags({'prompt_key': prompt_key[0]})
            flow_span.set_tags({'prompt_version': prompt_key[1]})
            flow_span.set_tags({'prompt_provider': 'cozeloop'})
        elif all(name in kwargs.get('metadata', {}) for name in ('lc_hub_owner', 'lc_hub_repo', 'lc_hub_commit_hash')):
            flow_span.set_tags(
                {'prompt_key': kwargs['metadata']['lc_hub_owner'] + '/' + kwargs['metadata']['lc_hub_repo']})
            flow_span.set_tags({'prompt_version': kwargs['metadata']['lc_hub_commit_hash']})
            flow_span.set_tags({'prompt_provider': 'langsmith'})

    def _new_flow_span(self, node_name: str, span_type: str, **kwargs: Any) -> Span:
        span_type = _span_type_mapping(span_type)
        span_name = node_name
        # set parent span
        parent_span: Span = None
        is_root_span = False
        if 'parent_run_id' in kwargs and kwargs['parent_run_id'] is not None and str(kwargs['parent_run_id']) in self.run_map:
            parent_span = self.run_map[str(kwargs['parent_run_id'])].span
        # only root span use child_of
        if parent_span is None:
            is_root_span = True
            if self._child_of:
                parent_span = self._child_of
        # modify name
        error_tag = {}
        try:
            if self.name_fn:
                name = self.name_fn(node_name)
                if name:
                    span_name = name
        except Exception as e:
            error_tag = {'error_info': f'name_fn error {repr(e)}', 'error_trace': traceback.format_exc()}
        # new span
        flow_span = self._client.start_span(span_name, span_type, child_of=parent_span)
        if is_root_span:
            if hasattr(flow_span, 'context'):
                self.root_span_id = flow_span.context.span_id
            else:
                self.trace_id = flow_span.span_id
        run_id = str(kwargs['run_id'])
        self.run_map[run_id] = Run(run_id, flow_span, span_type)
        # set runtime
        flow_span.set_runtime(RuntimeInfo())
        # set extra tags
        flow_span.set_tags(self._tags)  # global tags
        try:
            if self.tags_fn:  # add tags fn
                tags = self.tags_fn(node_name)
                if isinstance(tags, dict):
                    flow_span.set_tags(tags)
        except Exception as e:
            error_tag = {'error_info': f'tags_fn error {repr(e)}', 'error_trace': traceback.format_exc()}
        if error_tag:
            flow_span.set_tags(error_tag)
        return flow_span

    def _get_flow_span(self, **kwargs: Any) -> Span:
        run_id = str(kwargs['run_id'])
        if run_id in self.run_map:
            return self.run_map[run_id].span
        return None

    def _set_span_tags(self, flow_span: Span, tags: Dict[str, Any], need_convert_tag_value=True) -> None:
        if tags is None:
            return
        for key, value in tags.items():
            report_value = value
            if need_convert_tag_value:
                report_value = _convert_tag_value(value)
            flow_span.set_tags({_span_tag_key_mapping(key): report_value})

    def _set_extra_span_tags(self, flow_span: Span, tag_list: list, **kwargs: Any):
        if kwargs is None or len(kwargs) == 0:
            return
        for tag in tag_list:
            if tag in kwargs:
                flow_span.set_tags({_span_tag_key_mapping(tag): _convert_tag_value(kwargs[tag])})


class Run:
    def __init__(self, run_id: str, span: Span, span_type: str) -> None:
        self.run_id = run_id  # langchain run_id
        if hasattr(span, 'context'):
            self.span_id = span.context.span_id
        else:
            self.span_id = span.span_id  # loop span_id，the relationship between run_id and span_id is one-to-one mapping.
        self.span = span
        self.span_type = span_type
        self.child_runs: List[Run] = Field(default_factory=list)
        self.model_meta: Optional[ModelMeta] = None


def _get_value_from_json(json_data, key):
    if isinstance(json_data, dict):
        for k, v in json_data.items():
            if k == key:
                return v
        for k, v in json_data.items():
            if k == key:
                return v
            elif isinstance(v, dict) or isinstance(v, list):
                result = _get_value_from_json(v, key)
                if result is not None:
                    return result
    elif isinstance(json_data, list):
        results = []
        for item in json_data:
            result = _get_value_from_json(item, key)
            if result is not None:
                results.append(result)
        if len(results) > 0:
            return results
    return None


def _lc_prompt_role_converter(class_name: str) -> str:
    if class_name == SystemMessagePromptTemplate.__name__:
        return 'system'
    if class_name == HumanMessagePromptTemplate.__name__:
        return 'human'
    if class_name == AIMessagePromptTemplate.__name__:
        return 'ai'
    return class_name


def _span_type_mapping(span_type: str) -> str:
    """
    Map the span_type from Langchain to the span_type in Loop.
    """
    if span_type == 'ChatPromptTemplate':
        return 'prompt'
    elif span_type == 'model' or span_type == 'azure-openai-chat' or span_type == 'AzureChatOpenAI':
        return 'model'
    elif span_type == 'ReActSingleInputOutputParser':
        return 'parser'
    elif span_type == 'tool':
        return 'tool'
    return span_type


def _span_tag_key_mapping(span_tag_key: str) -> str:
    """
    Map the span_tag from Langchain to the span_tag in Loop.
    """
    if span_tag_key == 'prompt_tokens':
        return 'input_tokens'
    elif span_tag_key == 'completion_tokens':
        return 'output_tokens'
    elif span_tag_key == 'total_tokens':
        return 'tokens'
    elif span_tag_key == 'azure_deployment':
        return 'model_name'
    elif span_tag_key == 'invocation_param':
        return 'call_options'
    return span_tag_key


def _convert_tag_value(tag_value: Any) -> Any:
    if isinstance(tag_value, (bool, int, float)):
        return str(tag_value)
    return tag_value


def _convert_model_provider(type: str) -> str:
    if type == 'azure-openai-chat':
        return 'openai'
    return type


def _get_model_span_tags(**kwargs: Any) -> dict:
    invocation_params = kwargs.get('invocation_params', {})
    span_tags = {'call_options': {}}
    # set call_options span_tag
    for k, v in invocation_params.items():
        if k in ['temperature', 'top_p', 'n', 'max_tokens', 'stop'] and v is not None:
            span_tags['call_options'][k] = v
    span_tags['call_options'] = json.dumps(span_tags['call_options'], sort_keys=False, ensure_ascii=False)
    # set stream span_tag
    if 'stream' in invocation_params:
        span_tags['stream'] = str(invocation_params['stream']).lower()
    # set model_name span_tag
    if invocation_params.get('azure_deployment', None) is not None:
        if invocation_params.get('azure_deployment') == 'gpt_openapi':
            span_tags['model_name'] = invocation_params.get('model_name', invocation_params.get('model', ''))
        else:
            span_tags['model_name'] = invocation_params['azure_deployment']
    elif invocation_params.get('model_name', None) is not None:
        model_name = invocation_params['model_name']
        model_name = model_name[len('models/'):] if model_name.startswith('models/') else model_name
        span_tags['model_name'] = model_name
    elif invocation_params.get('model', None) is not None:
        model_name = invocation_params['model']
        model_name = model_name[len('models/'):] if model_name.startswith('models/') else model_name
        span_tags['model_name'] = model_name
    # set model_provider span_tag
    if '_type' in invocation_params:
        span_tags['model_provider'] = _convert_model_provider(invocation_params['_type'])
    return span_tags


def _convert_2_json(inputs: Any) -> str:
    try:
        format_input = _convert_inputs(inputs)
        if isinstance(format_input, str):
            return format_input
        else:
            return json.dumps(format_input,
                              default=lambda o: dict((key, value) for key, value in o.__dict__.items() if value),
                              ensure_ascii=False)
    except Exception as e:
        return repr(e)


def _convert_inputs(inputs: Any) -> Any:
    if isinstance(inputs, (str, bool, int, float)):
        return inputs
    if isinstance(inputs, dict):
        format_inputs = {}
        for key, val in inputs.items():
            format_inputs[key] = _convert_inputs(val)
        return format_inputs
    if isinstance(inputs, list) or isinstance(inputs, set):
        format_inputs = []
        for each in inputs:
            format_inputs.append(_convert_inputs(each))
        return format_inputs
    if isinstance(inputs, (AIMessageChunk, AIMessage)):
        """
        Must be before BaseMessage.
        """
        format_inputs = {
            'tool_calls': inputs.tool_calls,
            'invalid_tool_calls': inputs.invalid_tool_calls,
            'type': inputs.type,
        }
        if inputs.content != '':
            format_inputs['content'] = inputs.content
        return format_inputs
    if isinstance(inputs, BaseMessage):
        message = Message(role=inputs.type, content=inputs.content,
                          tool_calls=inputs.additional_kwargs.get('tool_calls', []))
        return message
    if isinstance(inputs, ChatPromptValue):
        return _convert_inputs(inputs.messages)
    if isinstance(inputs, (AgentAction, AgentFinish)):
        format_inputs = {}
        for key, val in vars(inputs).items():
            format_inputs[key] = _convert_inputs(val)
        return format_inputs
    if isinstance(inputs, tuple):
        format_inputs = []
        for i, val in enumerate(inputs):
            format_inputs.append(_convert_inputs(val))
        return format_inputs
    if isinstance(inputs, PromptValue):
        return _convert_inputs(inputs.to_messages())
    if isinstance(inputs, BaseModel):
        if pydantic.VERSION.startswith('1'):
            return inputs.json()
        else:
            return inputs.model_dump_json()
    if inputs is None:
        return 'None'
    return str(inputs)
