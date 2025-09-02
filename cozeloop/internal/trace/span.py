# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
from abc import ABC
from typing import Dict, Any, List, Optional
from datetime import datetime
import threading
import json
import urllib.parse

import pydantic

from cozeloop import span
from cozeloop.internal.trace.model.model import TagTruncateConf
from cozeloop.spec.tracespec import (ModelInput, ModelOutput, ModelMessagePartType, ModelMessage, ModelMessagePart,
                                     ModelImageURL, ModelFileURL, ModelChoice, Runtime, ERROR, PROMPT_KEY,
                                     PROMPT_VERSION, MODEL_PROVIDER, MODEL_NAME, RUNTIME_, CALL_OPTIONS,
                                     V_SCENE_CUSTOM, V_LANG_PYTHON)
from cozeloop.entities.prompt import Prompt
from cozeloop.internal.consts import *
from cozeloop.internal.trace.noop_span import NoopSpan
from cozeloop.internal.utils import get_tag_value_size_limit, truncate_string_by_byte, get_tag_key_size_limit, to_json
from cozeloop.internal.utils.validation import is_valid_url, is_valid_hex_str, parse_valid_mdn_base64
from cozeloop.internal.version import VERSION

logger = logging.getLogger(__name__)

spanUnFinished = 0
spanFinished = 1


class SpanContext(span.SpanContext):
    def __init__(self, trace_id: str, span_id: str, baggage: Dict[str, str] = None):
        if baggage is None:
            baggage = {}
        self.trace_id = trace_id
        self.span_id = span_id
        self._baggage = baggage

    def trace_id(self) -> str:
        return self.trace_id

    def span_id(self) -> str:
        return self.span_id

    @property
    def baggage(self) -> Dict[str, str]:
        return self._baggage

    @baggage.setter
    def baggage(self, value: Dict[str, str]):
        self._baggage = value

    def set_baggage_item(self, key: str, value: str):
        self._baggage[key] = value


class Span(span.Span, SpanContext, ABC):
    def __init__(self, span_type: str = '', name: str = '', space_id: str = '', trace_id: str = '', span_id: str = '',
                 parent_span_id: str = '', start_time: datetime = None, duration: int = 0,
                 baggage: Dict[str, str] = None, tag_map: Dict[str, Any] = None, system_tag_map: Dict[str, Any] = None,
                 status_code: int = 0, multi_modality_key_map: Dict[str, Any] = None,
                 ultra_large_report: bool = False, span_processor: Any = None, flags: int = 0,
                 is_finished: int = 0, *, service_name: str = '', log_id: str = '',
                 tag_truncate_conf: Optional[TagTruncateConf] = None):
        # span context param
        super().__init__(trace_id, span_id, baggage)

        # basic param
        self.span_type = span_type
        self.name = name

        # These params can be changed, but remember locking when changed
        self.service_name = service_name
        self.log_id = log_id
        self.space_id = space_id
        self.parent_span_id = parent_span_id
        self.start_time = start_time if start_time else datetime.now()
        self.duration = duration
        self.tag_map = tag_map if tag_map else {}
        self.system_tag_map = system_tag_map if system_tag_map else {}
        self.status_code = status_code

        # These params is internal field
        self.multi_modality_key_map = multi_modality_key_map if multi_modality_key_map else {}
        self.ultra_large_report = ultra_large_report
        self.span_processor = span_processor
        self.flags = flags
        self.is_finished = is_finished
        self.lock = threading.RLock()
        self.bytes_size: int = 0
        self.tag_truncate_conf = tag_truncate_conf

    def set_tags(self, tag_kv: Dict[str, Any]):
        if not tag_kv:
            return
        try:
            with self.lock:
                self.add_default_tag(tag_kv)
                rectified_map, cut_off_keys, size = self.get_rectified_map(tag_kv)
                self.bytes_size += size
                if cut_off_keys:
                    self.set_cut_off_tag(cut_off_keys)
                for key, value in rectified_map.items():
                    self.set_tag_item(key, value)
        except Exception as e:
            logger.error(f"Failed to set tags: {e}")

    def add_default_tag(self, tag_kv: Dict[str, Any]):
        for key, value in tag_kv.items():
            if key == ERROR:
                if self.status_code == 0:
                    self.status_code = STATUS_CODE_ERROR_DEFAULT

    def set_cut_off_tag(self, cut_off_keys: List[str]):
        try:
            if cut_off_tags := self.system_tag_map.get(CUT_OFF):
                if isinstance(cut_off_tags, list):
                    cut_off_keys.extend(cut_off_tags)
            self.system_tag_map[CUT_OFF] = list(set(cut_off_keys))
        except Exception as e:
            logger.error(f"Failed to set cut off tags: {e}")

    def set_tag_item(self, key: str, value: Any):
        try:
            if len(self.tag_map) < MAX_TAG_KV_COUNT_IN_ONE_SPAN:
                self.set_tag_unlock(key, value)
            else:
                logger.error(f"[trace] tag count exceed limit:{MAX_TAG_KV_COUNT_IN_ONE_SPAN}")
                pass
        except Exception as e:
            logger.error(f"Failed to set tag item: {e}")

    def set_tag_unlock(self, key: str, value: Any):
        self.tag_map[key] = value

    def get_tag_map(self) -> Dict[str, Any]:
        return self.tag_map

    def get_duration(self) -> int:
        return self.duration

    def get_space_id(self) -> str:
        return self.space_id

    def get_span_name(self) -> str:
        return self.name

    def get_span_type(self) -> str:
        return self.span_type

    def get_status_code(self) -> int:
        return self.status_code

    def ultra_large_report(self) -> bool:
        return self.ultra_large_report

    def baggage(self) -> Dict[str, str]:
        return super().baggage

    def set_input(self, input_data):
        if self is None:
            return None

        try:
            message_parts = []
            m_content = ModelInput()
            if isinstance(input_data, ModelInput):
                m_content = input_data
                for message in input_data.messages:
                    if message.parts:
                        message_parts.extend(message.parts)

            is_multi_modality = self.parse_model_message_parts(message_parts)

            if is_multi_modality:
                self.set_multi_modality_map(INPUT)
                size = self.get_model_input_bytes_size(self.deep_copy_message_of_model_input(m_content))
                with self.lock:
                    self.bytes_size += size

            self.set_tags({INPUT: input_data})
        except Exception as e:
            logger.error(f"Failed to set input: {e}")
        return None

    def deep_copy_message_of_model_input(self, src: ModelInput) -> ModelInput:
        result = ModelInput()
        result.messages = [ModelMessage(parts=[ModelMessagePart(
            type=part.type,
            text=part.text,
            image_url=ModelImageURL(
                name=part.image_url.name,
                url=part.image_url.url,
                detail=part.image_url.detail
            ) if part.image_url else None,
            file_url=ModelFileURL(
                name=part.file_url.name,
                url=part.file_url.url,
                detail=part.file_url.detail,
                suffix=part.file_url.suffix
            ) if part.file_url else None
        ) for part in message.parts]) for message in src.messages]

        result.tools = src.tools
        result.model_tool_choice = src.model_tool_choice
        return result

    def get_model_input_bytes_size(self, m_content):
        for message in m_content.messages:
            if message is None:
                continue
            for part in message.parts:
                if part is None:
                    continue
                if part.type == ModelMessagePartType.IMAGE and part.image_url and part.image_url.url:
                    part.image_url.url = ""
                elif part.type == ModelMessagePartType.FILE and part.file_url and part.file_url.url:
                    part.file_url.url = ""

        try:
            m_content_json = ""
            if pydantic.VERSION.startswith('1'):
                m_content_json = m_content.json()
            else:
                m_content_json = m_content.model_dump_json()
            return len(m_content_json)
        except Exception as e:
            logger.error(f"Failed to get model input size, m_content model_dump_json err: {e}")
            return 0

    def parse_model_message_parts(self, contents: List[Any]) -> bool:
        is_multi_modality = False
        for content in contents:
            if content.type == ModelMessagePartType.IMAGE:
                if content.image_url and content.image_url.url:
                    base64_data, is_base64 = parse_valid_mdn_base64(content.image_url.url)
                    if is_base64:
                        content.image_url.url = base64_data
                        is_multi_modality = True
                    if is_valid_url(content.image_url.url):
                        is_multi_modality = True
            elif content.type == ModelMessagePartType.FILE:
                if content.file_url and content.file_url.url:
                    base64_data, is_base64 = parse_valid_mdn_base64(content.file_url.url)
                    if is_base64:
                        content.file_url.url = base64_data
                        is_multi_modality = True
                    if is_valid_url(content.file_url.url):
                        is_multi_modality = True
        return is_multi_modality

    def set_output(self, output):
        if self is None:
            return None

        try:
            m_content = ModelOutput()
            message_parts = []

            if isinstance(output, ModelOutput):
                m_content = output
                for choice in output.choices:
                    if choice.message:
                        message_parts.extend(choice.message.parts)
            is_multi_modality = self.parse_model_message_parts(message_parts)
            if is_multi_modality:
                self.set_multi_modality_map(OUTPUT)
                size = self.get_model_output_bytes_size(self.deep_copy_message_of_model_output(m_content))
                with self.lock:
                    self.bytes_size += size
            self.set_tags({OUTPUT: output})
        except Exception as e:
            logger.error(f"Failed to set output: {e}")
        return None

    def deep_copy_message_of_model_output(self, src):
        result = ModelOutput()
        result.choices = [ModelChoice(
            message=ModelMessage(
                parts=[ModelMessagePart(
                    type=part.type,
                    text=part.text,
                    image_url=ModelImageURL(
                        name=part.image_url.name,
                        url=part.image_url.url,
                        detail=part.image_url.detail
                    ) if part.image_url else None,
                    file_url=ModelFileURL(
                        name=part.file_url.name,
                        url=part.file_url.url,
                        detail=part.file_url.detail,
                        suffix=part.file_url.suffix
                    ) if part.file_url else None
                ) for part in choice.message.parts]
            ) if choice.message else None
        ) for choice in src.choices]

        return result

    def get_model_output_bytes_size(self, m_content):
        for choice in m_content.choices:
            if choice.message is None:
                continue
            for part in choice.message.parts:
                if part is None:
                    continue
                if part.type == ModelMessagePartType.IMAGE and part.image_url and part.image_url.url:
                    part.image_url.url = ''
                elif part.type == ModelMessagePartType.FILE and part.file_url and part.file_url.url:
                    part.file_url.url = ''

        try:
            m_content_json = json.dumps(m_content)
            return len(m_content_json)
        except Exception:
            return 0

    def set_error(self, err: Exception):
        self.set_tags({ERROR: err.__str__()})

    def set_status_code(self, code: int):
        with self.lock:
            self.status_code = code

    def set_user_id(self, user_id: str):
        self.set_tags({USER_ID: user_id})

    def set_user_id_baggage(self, user_id: str):
        self.set_baggage({USER_ID: user_id})

    def set_message_id(self, message_id: str):
        self.set_tags({MESSAGE_ID: message_id})

    def set_message_id_baggage(self, message_id: str):
        self.set_baggage({MESSAGE_ID: message_id})

    def set_thread_id(self, thread_id: str):
        self.set_tags({THREAD_ID: thread_id})

    def set_thread_id_baggage(self, thread_id: str):
        self.set_baggage({THREAD_ID: thread_id})

    def set_prompt(self, prompt: Prompt):
        if prompt.prompt_key:
            self.set_tags({PROMPT_KEY: prompt.prompt_key})
            if prompt.version:
                self.set_tags({PROMPT_VERSION: prompt.version})

    def set_model_provider(self, model_provider: str):
        self.set_tags({MODEL_PROVIDER: model_provider})

    def set_model_name(self, model_name: str):
        self.set_tags({MODEL_NAME: model_name})

    def set_model_call_options(self, model_call_options: Any):
        self.set_tags({CALL_OPTIONS: model_call_options})

    def set_input_tokens(self, input_tokens: int):
        self.set_tags({INPUT_TOKENS: input_tokens})

    def set_output_tokens(self, output_tokens: int):
        self.set_tags({OUTPUT_TOKENS: output_tokens})

    def set_start_time_first_resp(self, start_time_first_resp: int):
        self.set_tags({START_TIME_FIRST_RESP: start_time_first_resp})

    def set_runtime(self, runtime: Runtime) -> None:
        r = runtime
        r.scene = V_SCENE_CUSTOM
        with self.lock:
            if self.system_tag_map is None:
                self.system_tag_map = {}
            self.system_tag_map[RUNTIME_] = r

    def set_service_name(self, service_name: str) -> None:
        self.service_name = service_name

    def set_log_id(self, log_id: str) -> None:
        self.log_id = log_id

    def set_system_tags(self, system_tags: Dict[str, Any]) -> None:
        if not system_tags:
            return
        with self.lock:
            if self.system_tag_map is None:
                self.system_tag_map = {}
            for key, value in system_tags.items():
                self.system_tag_map[key] = value

    def set_deployment_env(self, deployment_env: str) -> None:
        self.set_tags({DEPLOYMENT_ENV: deployment_env})

    def get_rectified_map(self, input_map: Dict[str, Any]) -> (Dict[str, Any], List[str], int):
        validate_map = {}
        cut_off_keys = []
        bytes_size = 0

        for key, value in input_map.items():
            if key in RESERVE_FIELD_TYPES:
                expected_types = RESERVE_FIELD_TYPES[key]
                if type(value) not in expected_types:
                    logger.error(f"The value for field [{key}] is not in the correct format, type:{type(value)}, expectedType:{expected_types}")
                    continue

            value_str = ''
            if self.is_can_cut_off(value):
                value_str = to_json(value)
                value = value_str

            # Truncate the value if a single tag's value is too large
            tag_value_length_limit = self.get_tag_value_size_limit(key)
            is_ultra_large_report = False
            v, is_truncate = truncate_string_by_byte(value_str, tag_value_length_limit)
            if is_truncate:
                if key not in self.multi_modality_key_map and self.ultra_large_report:
                    is_ultra_large_report = True
                if key not in self.multi_modality_key_map and not self.ultra_large_report:
                    value = v
                    cut_off_keys.append(key)
                    logger.warning(f"field value [{key}] is too long, and opt.EnableLongReport is false, so value has been truncated to {tag_value_length_limit} size")

            # Truncate the key if a single tag's key is too large
            tag_key_length_limit = get_tag_key_size_limit()
            key, is_truncate = truncate_string_by_byte(key, tag_key_length_limit)
            if is_truncate:
                cut_off_keys.append(key)
                logger.warning(f"field key [{key}] is too long, and opt.EnableLongReport is false, so key has been truncated to {tag_key_length_limit} size")

            validate_map[key] = value

            bytes_size += len(key)
            if key not in self.multi_modality_key_map and not is_ultra_large_report:
                bytes_size += len(value_str)

        return validate_map, cut_off_keys, bytes_size

    def is_can_cut_off(self, value: Any) -> bool:
        return value is not None and not isinstance(value, (int, float, bool))

    def get_tag_value_size_limit(self, key: str) -> int:
        limit = get_tag_value_size_limit(key)
        if key == INPUT or key == OUTPUT:
            if self.tag_truncate_conf and self.tag_truncate_conf.input_output_field_max_byte > 0:
                limit = self.tag_truncate_conf.input_output_field_max_byte
        else:
            if self.tag_truncate_conf and self.tag_truncate_conf.normal_field_max_byte > 0:
                limit = self.tag_truncate_conf.normal_field_max_byte
        return limit

    def set_multi_modality_map(self, key: str):
        with self.lock:
            if not self.multi_modality_key_map:
                self.multi_modality_key_map = {}
            self.multi_modality_key_map[key] = True

    def set_baggage(self, baggage_item: Dict[str, str]):
        if not baggage_item:
            return
        self.set_baggage_escape(baggage_item, True)

    def set_baggage_escape(self, baggage_item: Dict[str, str], escape: bool):
        if not baggage_item:
            return
        try:
            for key, value in baggage_item.items():
                if self.is_valid_baggage_item(key, value):
                    self.set_tags({key: value})
                    if escape:
                        key = urllib.parse.quote(key)
                        value = urllib.parse.quote(value)
                    self.set_baggage_item(key, value)
                else:
                    logger.error(f"[trace] invalid baggageItem:{key}:{value}")
                    pass
        except Exception as e:
            logger.error(f"Failed to set_baggage_escape: {e}")

    def is_valid_baggage_item(self, key: str, value: str) -> bool:
        key_limit = get_tag_key_size_limit()
        value_limit = get_tag_value_size_limit(key)
        if len(key) > key_limit or len(value) > value_limit:
            logger.info(f"[trace] length of Baggage is too large, key:{key}, value:{value}")
            return False

        if any(special_char in key for special_char in BAGGAGE_SPECIAL_CHARS):
            logger.error(f"[trace] baggage should not contain special characters, key:{key}, value:{value}")
            return False

        return True

    def set_baggage_item(self, restricted_key: str, value: str):
        with self.lock:
            super().set_baggage_item(restricted_key, value)

    def finish(self):
        try:
            if not self.is_do_finish():
                return

            delete_span_in_context(self.span_id)

            self.set_system_tag()
            self.set_stat_info()
            self.span_processor.on_span_end(self)
        except Exception as e:
            logger.error(f"Failed to finish span: {e}")

    def is_do_finish(self):
        with self.lock:
            if self.is_finished == spanUnFinished:
                self.is_finished = spanFinished
                return True
            return False

    def set_system_tag(self):
        if self.system_tag_map is None:
            self.system_tag_map = {}

        runtime = Runtime()
        runtime_obj = self.system_tag_map.get(RUNTIME_)
        if runtime_obj is not None and isinstance(runtime_obj, Runtime):
            runtime = runtime_obj

        runtime.language = V_LANG_PYTHON
        if not runtime.scene:
            runtime.scene = V_SCENE_CUSTOM
        runtime.loop_sdk_version = VERSION

        with self.lock:
            self.system_tag_map[RUNTIME_] = to_json(runtime)

    def set_stat_info(self):
        tag_map = self.get_tag_map()
        if start_time_first_resp := tag_map.get(START_TIME_FIRST_RESP):
            latency_first_resp = int(start_time_first_resp) - int(self.start_time.timestamp() * 1000000)
            self.set_tags({LATENCY_FIRST_RESP: latency_first_resp})

        input_tokens = tag_map.get(INPUT_TOKENS, 0)
        output_tokens = tag_map.get(OUTPUT_TOKENS, 0)
        if input_tokens > 0 or output_tokens > 0:
            self.set_tags({TOKENS: int(input_tokens) + int(output_tokens)})

        duration = int((datetime.now().timestamp() - self.start_time.timestamp()) * 1000000)
        with self.lock:
            self.duration = duration

    def trace_id(self) -> str:
        return super().trace_id()

    def span_id(self) -> str:
        return super().span_id()

    def start_time(self) -> datetime:
        return self.start_time

    def to_header(self) -> Dict[str, str]:
        res = {
            TRACE_CONTEXT_HEADER_PARENT: self.to_header_parent(),
            TRACE_CONTEXT_HEADER_BAGGAGE: self.to_header_baggage()
        }
        return res

    def to_header_baggage(self) -> str:
        if not self.baggage:
            return ""
        return ",".join(f"{k}={v}" for k, v in self.baggage().items() if k and v)

    def to_header_parent(self) -> str:
        return f"{GLOBAL_TRACE_VERSION:02x}-{self.trace_id}-{self.span_id}-{self.flags:02x}"

    def is_root_span(self) -> bool:
        return self.parent_span_id is None or self.parent_span_id == '' or self.parent_span_id == '0'

    def __enter__(self):
        return self

    def __exit__(self, exc, value, tb):
        self.finish()


def from_header(h: Dict[str, str]) -> span.Span:
    try:
        header = {canonical_mime_header_key(k): v for k, v in h.items()}
        sp = Span()

        if header_parent := header.get(TRACE_CONTEXT_HEADER_PARENT):
            trace_id, span_id = from_header_parent(header_parent)
            sp.trace_id = trace_id
            sp.span_id = span_id

        if header_baggage := header.get(TRACE_CONTEXT_HEADER_BAGGAGE):
            sp.baggage = from_header_baggage(header_baggage)

        return sp
    except Exception as e:
        logger.error(f"Failed to from_header: {e}")
        return NoopSpan()


def canonical_mime_header_key(header_key):
    return '-'.join(word.capitalize() for word in header_key.split('-'))


def from_header_parent(h: str) -> (str, str):
    parts = h.split("-")
    if len(parts) != 4:  # bad data
        return "", ""

    trace_id_temp = parts[1]
    if len(trace_id_temp) != 32 or trace_id_temp == "00000000000000000000000000000000":
        return "", "", Exception(f"invalid trace id: {trace_id_temp}")
    if not is_valid_hex_str(trace_id_temp):
        return "", "", Exception(f"invalid trace id: {trace_id_temp}")

    span_id_temp = parts[2]
    if len(span_id_temp) != 16 or span_id_temp == "0000000000000000":
        return "", "", Exception(f"invalid span id: {span_id_temp}")
    if not is_valid_hex_str(span_id_temp):
        return "", "", Exception(f"invalid span id: {span_id_temp}")

    return trace_id_temp, span_id_temp


def from_header_baggage(h: str) -> Dict[str, str]:
    return parse_comma_separated_map(h, True)


def parse_comma_separated_map(src: str, cover: bool) -> Dict[str, str]:
    baggage = {}
    for item in src.split(","):
        kv = item.strip().split("=")
        if len(kv) != 2:
            continue

        key = urllib.parse.unquote(kv[0])
        value = urllib.parse.unquote(kv[1])

        if not key or not value:
            continue

        if key not in baggage or cover:
            baggage[key] = value

    return baggage


# LinkedList in contextvars
class Node:
    def __init__(self, data: Span):
        self.data = data
        self.next = None
        self.prev = None

class DoublyLinkedList:
    def __init__(self):
        self.head = None
        self.tail = None

    def append(self, data: Span):
        """append to tail"""
        new_node = Node(data)
        if not self.head:
            self.head = new_node
            self.tail = new_node
        else:
            self.tail.next = new_node
            new_node.prev = self.tail
            self.tail = new_node

    def get_tail(self):
        """get tail node"""
        return self.tail

    def delete_node(self, span_id: str):
        """delete node by span_id"""
        current_node = self.head

        while current_node and current_node.data.span_id != span_id:
            current_node = current_node.next

        if current_node is None:
            return

        if current_node == self.head:
            self.head = current_node.next
            if self.head:
                self.head.prev = None
            else:
                self.tail = None
        elif current_node == self.tail:
            self.tail = current_node.prev
            if self.tail:
                self.tail.next = None
            else:
                self.head = None
        else:
            current_node.prev.next = current_node.next
            current_node.next.prev = current_node.prev

        current_node = None


span_ctx = ContextVar('loop_span', default=None)


def get_newest_span_from_context() -> Span:
    linked_list = span_ctx.get(None)
    if linked_list and linked_list.get_tail() is not None:
        return linked_list.get_tail().data
    return None

def set_span_to_context(span: Span):
    linked_list = span_ctx.get(None)
    if linked_list:
        linked_list.append(span)
    else:
        linked_list = DoublyLinkedList()
        linked_list.append(span)
        span_ctx.set(linked_list)

def delete_span_in_context(span_id: str):
    linked_list = span_ctx.get(None)
    if linked_list:
        linked_list.delete_node(span_id)
    span_ctx.set(linked_list)
