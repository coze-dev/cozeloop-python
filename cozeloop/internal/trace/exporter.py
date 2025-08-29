# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import base64
import logging
import time
from typing import Dict, List, Optional, Tuple, Callable, Any

import pydantic

from cozeloop.spec.tracespec import ModelInput, ModelMessagePart, ModelMessagePartType, ModelImageURL, ModelFileURL, ModelOutput
from cozeloop.internal.consts import *
from cozeloop.internal.httpclient import Client, BaseResponse
from cozeloop.internal.trace.model.model import UploadType, Attachment, ObjectStorage
from cozeloop.internal.trace.span import Span
from cozeloop.internal.utils.convert import truncate_string_by_char
from cozeloop.internal.utils.get import gen_16char_id
from cozeloop.internal.utils.validation import is_valid_url

logger = logging.getLogger(__name__)


class UploadSpan(BaseModel):
    started_at_micros: int
    log_id: str
    span_id: str
    parent_id: str
    trace_id: str
    duration_micros: int
    service_name: str
    workspace_id: str
    span_name: str
    span_type: str
    status_code: int
    input: str
    output: str
    object_storage: str
    system_tags_string: Dict[str, str]
    system_tags_long: Dict[str, int]
    system_tags_double: Dict[str, float]
    tags_string: Dict[str, str]
    tags_long: Dict[str, int]
    tags_double: Dict[str, float]
    tags_bool: Dict[str, bool]


class UploadSpanData(BaseModel):
    spans: List['UploadSpan']


class Exporter:
    def export_spans(self, ctx: dict, spans: List['UploadSpan']):
        raise NotImplementedError

    def export_files(self, ctx: dict, files: List['UploadFile']):
        raise NotImplementedError


KEY_TEMPLATE_LARGE_TEXT = "%s_%s_%s_%s_large_text"
KEY_TEMPLATE_MULTI_MODALITY = "%s_%s_%s_%s_%s"

FILE_TYPE_TEXT = "text"
FILE_TYPE_IMAGE = "image"
FILE_TYPE_FILE = "file"

PATH_INGEST_TRACE = "/v1/loop/traces/ingest"
PATH_UPLOAD_FILE = "/v1/loop/files/upload"

class UploadPath:
    def __init__(
            self,
            span_upload_path: str,
            file_upload_path: str,
    ):
        self.span_upload_path = span_upload_path
        self.file_upload_path = file_upload_path


class SpanExporter(Exporter):
    def __init__(
            self,
            client: Client,
            upload_path: UploadPath,
    ):
        self.client = client
        self.upload_path = upload_path

    def export_files(self, ctx: dict, files: List['UploadFile']):
        for file in files:
            if not file:
                continue

            logger.debug(f"uploadFile start, file name: {file.name}")
            try:
                resp = self.client.upload_file(
                    self.upload_path.file_upload_path,
                    BaseResponse,
                    file.data,
                    file.tos_key,
                    {"workspace_id": file.space_id},
                )
                if resp.code != 0: # todo: some err code do not need retry
                    raise Exception(f"code:[{resp.code}], msg:[{resp.msg}]")
            except Exception as e:
                raise Exception(f"export files[{file.tos_key}] fail, err:[{e}], file.name:[{file.name}]")

            logger.debug(f"uploadFile end, file name: {file.name}")


    def export_spans(self, ctx: dict, spans: List['UploadSpan']):
        if not spans or len(spans) == 0:
            return

        try:
            resp = self.client.post(
                self.upload_path.span_upload_path,
                BaseResponse,
                UploadSpanData(spans=spans),
            )
            if resp.code != 0: # todo: some err code do not need retry
                raise Exception(f"code:[{resp.code}], msg:[{resp.msg}]")
        except Exception as e:
            raise Exception(f"export spans fail, err:[{e}]")


class UploadFile(BaseModel):
    class Config:
        arbitrary_types_allowed = True
    tos_key: str
    data: bytes
    upload_type: UploadType
    tag_key: str
    name: str
    file_type: str
    space_id: str


def transfer_to_upload_span_and_file(spans: List['Span']) -> (List[UploadSpan], List[UploadFile]):
    res_span = []
    res_file = []

    for span in spans:
        span_upload_files, put_content_map = parse_input_output(span)
        object_storage_byte = transfer_object_storage(span_upload_files)

        tag_str_m, tag_long_m, tag_double_m, tag_bool_m = parse_tag(span.tag_map, False)
        system_tag_str_m, system_tag_long_m, system_tag_double_m, _ = parse_tag(span.system_tag_map, True)

        res_span.append(UploadSpan(
            started_at_micros=int(span.start_time.timestamp() * 1_000_000),
            log_id=span.log_id,
            span_id=span.span_id,
            parent_id=span.parent_span_id,
            trace_id=span.trace_id,
            duration_micros=span.get_duration(),
            service_name=span.service_name,
            workspace_id=span.get_space_id(),
            span_name=span.get_span_name(),
            span_type=span.get_span_type(),
            status_code=span.get_status_code(),
            input=put_content_map.get(INPUT, ""),
            output=put_content_map.get(OUTPUT, ""),
            object_storage=object_storage_byte,
            system_tags_string=system_tag_str_m,
            system_tags_long=system_tag_long_m,
            system_tags_double=system_tag_double_m,
            tags_string=tag_str_m,
            tags_long=tag_long_m,
            tags_double=tag_double_m,
            tags_bool=tag_bool_m,
        ))
        res_file.extend(span_upload_files)

    return res_span, res_file


def parse_tag(span_tag: Dict[str, Any], is_system_tag: bool) -> (Dict[str, str], Dict[str, int], Dict[str, float], Dict[str, bool]):
    if not span_tag:
        return {}, {}, {}, {}

    v_str_map = {}
    v_long_map = {}
    v_double_map = {}
    v_bool_map = {}

    for key, value in span_tag.items():
        if key in (INPUT, OUTPUT):
            continue

        if isinstance(value, str):
            v_str_map[key] = value
        elif isinstance(value, bool):
            if is_system_tag:
                v_str_map[key] = str(value)
            else:
                v_bool_map[key] = bool(value)
        elif isinstance(value, int):
            v_long_map[key] = int(value)
        elif isinstance(value, float):
            v_double_map[key] = float(value)
        else:
            v_str_map[key] = str(value)

    return v_str_map, v_long_map, v_double_map, v_bool_map



def convert_input(span_key: str, span: Span) -> (str, List[UploadFile]):
    value = span.tag_map.get(span_key)
    if not value:
        return "", []

    upload_files = []
    if span_key not in span.multi_modality_key_map:
        value_res, f = transfer_text(str(value), span, span_key)
        if f:
            upload_files.append(f)
    else:
        model_input = ModelInput()
        if isinstance(value, str):
            try:
                if pydantic.VERSION.startswith('1'):
                    model_input = ModelInput.parse_raw(value)
                else:
                    model_input = ModelInput.model_validate_json(value)
            except Exception as e:
                logger.error(f"unmarshal ModelInput failed, err: {e}")
                return "", []

        for message in model_input.messages:
            for part in message.parts:
                files = transfer_message_part(part, span, span_key)
                upload_files.extend(files)

        if pydantic.VERSION.startswith('1'):
            value_res = model_input.json()
        else:
            value_res = model_input.model_dump_json()

        if len(value_res) > MAX_BYTES_OF_ONE_TAG_VALUE_OF_INPUT_OUTPUT:
            value_res, f = transfer_text(value_res, span, span_key)
            if f:
                upload_files.append(f)

    return value_res, upload_files



def convert_output(span_key: str, span: Span) -> (str, List[UploadFile]):
    value = span.tag_map.get(span_key)
    if not value:
        return "", []

    upload_files = []
    if span_key not in span.multi_modality_key_map:
        value_res, f = transfer_text(str(value), span, span_key)
        if f:
            upload_files.append(f)
    else:
        model_output = ModelOutput()
        if isinstance(value, str):
            try:
                if pydantic.VERSION.startswith('1'):
                    model_output = ModelOutput.parse_raw(value)
                else:
                    model_output = ModelOutput.model_validate_json(value)
            except Exception as e:
                logger.error(f"unmarshal ModelOutput failed, err: {e}")
                return "", []

        for choice in model_output.choices:
            if not choice or not choice.message:
                continue
            for part in choice.message.parts:
                files = transfer_message_part(part, span, span_key)
                upload_files.extend(files)

        value_res = model_output.to_json()

        if len(value) > MAX_BYTES_OF_ONE_TAG_VALUE_OF_INPUT_OUTPUT:
            value_res, f = transfer_text(value_res, span, span_key)
            if f:
                upload_files.append(f)

    return value_res, upload_files


class TagValueConverter(BaseModel):
    convert_func: Callable[[str, Span], Tuple[str, List[UploadFile]]]

tag_value_converter_map: Dict[str, TagValueConverter] = {
    INPUT: TagValueConverter(convert_func=convert_input),
    OUTPUT: TagValueConverter(convert_func=convert_output),
}


def parse_input_output(span: 'Span') -> (List[UploadFile], Dict[str, str]):
    if span is None:
        return [], {}

    span_upload_files = []
    put_content_map = {}

    for key, converter in tag_value_converter_map.items():
        if key not in span.get_tag_map():
            continue
        try:
            new_input, input_files = converter.convert_func(key, span)
        except Exception as e:
            logger.error(f"converter.convert_func failed, err: {e}")
            return [], {}
        put_content_map[key] = new_input
        span_upload_files.extend(input_files)

    return span_upload_files, put_content_map


def transfer_object_storage(span_upload_files: List[UploadFile]) -> str:
    if span_upload_files is None:
        return ""
    object_storage = ObjectStorage(attachments=[])
    is_exist = False

    for file in span_upload_files:
        if not file:
            continue

        is_exist = True
        if file.upload_type == UploadType.LONG:
            if file.tag_key == INPUT:
                object_storage.input_tos_key = file.tos_key
            elif file.tag_key == OUTPUT:
                object_storage.output_tos_key = file.tos_key
        elif file.upload_type == UploadType.MULTI_MODALITY:
            object_storage.attachments.append(Attachment(
                field=file.tag_key,
                name=file.name,
                type=file.file_type,
                tos_key=file.tos_key
            ))

    if not is_exist:
        return ""

    if pydantic.VERSION.startswith('1'):
        return object_storage.json()
    else:
        return object_storage.model_dump_json()


def transfer_message_part(src: ModelMessagePart, span: 'Span', tag_key: str) -> List[UploadFile]:
    if not src or not span:
        return []

    upload_files = []
    if src.type == ModelMessagePartType.IMAGE:
        f = transfer_image(src.image_url, span, tag_key)
        if f:
            upload_files.append(f)
    elif src.type == ModelMessagePartType.FILE:
        f = transfer_file(src.file_url, span, tag_key)
        if f:
            upload_files.append(f)
    else:
        return upload_files

    return upload_files


def transfer_text(src: str, span: 'Span', tag_key: str) -> (str, Optional[UploadFile]):
    if not src:
        return "", None

    if not span.ultra_large_report:
        return src, None

    src_byte= src.encode('utf-8')
    if len(src_byte) > MAX_BYTES_OF_ONE_TAG_VALUE_OF_INPUT_OUTPUT:
        key = KEY_TEMPLATE_LARGE_TEXT % (span.trace_id, span.span_id, tag_key, FILE_TYPE_TEXT)
        return truncate_string_by_char(src, TEXT_TRUNCATE_CHAR_LENGTH), UploadFile(
            tos_key=key,
            data=src_byte,
            upload_type=UploadType.LONG,
            tag_key=tag_key,
            name='',
            file_type=FILE_TYPE_TEXT,
            space_id=span.get_space_id()
        )

    return src, None


def transfer_image(src: ModelImageURL, span: 'Span', tag_key: str) -> Optional[UploadFile]:
    if not src or not span:
        return None

    if is_valid_url(src.url):
        return None

    key = KEY_TEMPLATE_MULTI_MODALITY % (
        span.trace_id, span.span_id, tag_key, FILE_TYPE_IMAGE, gen_16char_id())
    bin_data = base64.b64decode(src.url)
    src.url = key
    return UploadFile(
        tos_key=key,
        data=bin_data,
        upload_type=UploadType.MULTI_MODALITY,
        tag_key=tag_key,
        name=src.name,
        file_type=FILE_TYPE_IMAGE,
        space_id=span.space_id
    )


def transfer_file(src: ModelFileURL, span: 'Span', tag_key: str) -> Optional[UploadFile]:
    if not src or not span:
        return None

    if is_valid_url(src.url):
        return None

    key = KEY_TEMPLATE_MULTI_MODALITY % (
        span.trace_id, span.span_id, tag_key, FILE_TYPE_FILE, gen_16char_id())
    bin_data = base64.b64decode(src.url)
    src.url = key
    return UploadFile(
        tos_key=key,
        data=bin_data,
        upload_type=UploadType.MULTI_MODALITY,
        tag_key=tag_key,
        name=src.name,
        file_type=FILE_TYPE_FILE,
        space_id=span.space_id
    )