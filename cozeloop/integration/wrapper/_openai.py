import logging
from collections import defaultdict
from typing import Any, Callable, Optional
from functools import wraps

from cozeloop import get_span_from_context
from cozeloop.decorator import observe
from cozeloop.decorator.utils import is_async_func
from cozeloop.spec.tracespec import ModelCallOption

from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import Choice, ChoiceDeltaToolCall
from openai.types.responses import ResponseStreamEvent


def openai_wrapper(
        client: Any,
        *,
        chat_name: str = "ChatOpenAI",
) -> Any:
    model_provider = "openai"
    try:
        from openai import AsyncOpenAI, OpenAI, AsyncAzureOpenAI, AzureOpenAI
        if not isinstance(client, (AsyncOpenAI, OpenAI, AzureOpenAI, AsyncAzureOpenAI)):
            return client
        if isinstance(client, (AzureOpenAI, AsyncAzureOpenAI)):
            model_provider = "azure"
            if chat_name == "ChatOpenAI":
                chat_name = "AzureChatOpenAI"
    except Exception as e:
        logging.warning(f"import OpenAI error: {e}")
        return client

    client.chat.completions.create = _get_openai_wrapper(
        client.chat.completions.create,
        chat_name,
        model_provider,
        gen_tags_func=_get_openai_model_tags,
        process_inputs=_process_chat_completion_input,
        process_outputs=_process_chat_completion_output,
        process_iterator_outputs=_process_chat_completion_iter_output,
    )

    if hasattr(client, "responses"):
        if hasattr(client.responses, "create"):
            client.responses.create = _get_openai_wrapper(
                client.responses.create,
                chat_name,
                model_provider,
                gen_tags_func=_get_openai_model_tags,
                process_inputs=_process_chat_completion_input,
                process_outputs=_process_responses_output,
                process_iterator_outputs=_process_response_iter_output,
            )

    return client


def _get_openai_wrapper(
        original_func: Callable,
        name: str,
        model_provider: str,
        gen_tags_func: Optional[Callable] = None,
        process_inputs: Optional[Callable] = None,
        process_outputs: Optional[Callable] = None,
        process_iterator_outputs: Callable = None
) -> Callable:
    @wraps(original_func)
    def sync_create(*args, **kwargs):
        tags = gen_tags_func(model_provider, **kwargs)
        decorator = observe(
            name=name,
            span_type="model",
            tags=tags,
            process_inputs=process_inputs,
            process_outputs=process_outputs,
            process_iterator_outputs=process_iterator_outputs if kwargs.get("stream") is True else None,
        )

        return decorator(original_func)(*args, **kwargs)

    @wraps(original_func)
    async def async_create(*args, **kwargs):
        tags = gen_tags_func(model_provider, **kwargs)
        decorator = observe(
            name=name,
            span_type="model",
            tags=tags,
            process_inputs=process_inputs,
            process_outputs=process_outputs,
            process_iterator_outputs=process_iterator_outputs if kwargs.get("stream") is True else None,

        )
        return await decorator(original_func)(*args, **kwargs)

    return async_create if is_async_func(original_func) else sync_create


def _get_openai_model_tags(provider: str, **kwargs) -> dict[str, Any]:
    temperature = kwargs.get("temperature", 0.0)
    if not isinstance(temperature, float):
        temperature = float(temperature)
    stop_sequences = kwargs.get("stop")
    if stop_sequences and isinstance(stop_sequences, str):
        stop_sequences = [stop_sequences]
    opt = ModelCallOption(
        temperature=temperature,
        max_tokens=kwargs.get("max_tokens") or kwargs.get("max_completion_tokens") or kwargs.get("max_output_tokens"),
        stop=stop_sequences,
        top_p=kwargs.get("top_p"),
        n=kwargs.get("n"),
        frequency_penalty=kwargs.get("frequency_penalty"),
        presence_penalty=kwargs.get("presence_penalty"),
    )
    call_options = '{}'
    try:
        call_options = opt.model_dump_json()
    except Exception as e:
        pass

    return {
        "model_provider": provider,
        "model_name": kwargs.get("model"),
        "call_options": call_options,
        "stream": kwargs.get("stream", False),
    }


def _process_chat_completion_input(input: dict):
    return input.get('kwargs', '')


def _process_chat_completion_output(outputs: Any):
    try:
        output_dict = outputs.model_dump()
        usage = output_dict.pop("usage", None)
        output_dict["_inner_tokens_dict"] = (
            _create_inner_tokens_dict(usage) if usage else None
        )
        _compatibility_with_frontend(output_dict)
        return output_dict
    except BaseException as e:
        return outputs


def _compatibility_with_frontend(output_dict: Any):  # for compatibility with frontend render
    if output_dict.get("choices"):
        for choice in output_dict["choices"]:
            if choice.get("index") is None:
                choice["index"] = 0
            if choice.get("message") and choice["message"].get("tool_calls") is None:
                choice["message"]["tool_calls"] = []


def _create_inner_tokens_dict(token_usage: dict) -> dict:
    if not token_usage:
        return {}
    input_tokens = (
            token_usage.get("prompt_tokens") or token_usage.get("input_tokens") or 0
    )
    output_tokens = (
            token_usage.get("completion_tokens")
            or token_usage.get("output_tokens")
            or 0
    )
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def _process_chat_completion_iter_output(all_chunks: list[ChatCompletionChunk]) -> dict:
    choices_by_index: defaultdict[int, list[Choice]] = defaultdict(list)
    for chunk in all_chunks:
        for choice in chunk.choices:
            choices_by_index[choice.index].append(choice)
    if all_chunks:
        d = all_chunks[-1].model_dump()
        d["choices"] = [
            _convert_choices(choices) for choices in choices_by_index.values()
        ]
    else:
        d = {"choices": [{"message": {"role": "assistant", "content": ""}}]}
    oai_token_usage = d.pop("usage", None)
    d["_inner_tokens_dict"] = (
        _create_inner_tokens_dict(oai_token_usage) if oai_token_usage else None
    )
    return d


def _convert_choices(choices: list[Choice]) -> dict:
    reversed_choices = list(reversed(choices))
    message: dict[str, Any] = {
        "role": "assistant",
        "content": "",
    }
    for c in reversed_choices:
        if hasattr(c, "delta") and getattr(c.delta, "role", None):
            message["role"] = c.delta.role
            break
    tool_calls: defaultdict[int, list[ChoiceDeltaToolCall]] = defaultdict(list)
    for c in choices:
        if hasattr(c, "delta"):
            if getattr(c.delta, "content", None):
                message["content"] += c.delta.content
            if getattr(c.delta, "reasoning_content", None):
                if message.get("reasoning_content") is None:
                    message["reasoning_content"] = ""
                message["reasoning_content"] += c.delta.reasoning_content
            if getattr(c.delta, "function_call", None):
                if not message.get("function_call"):
                    message["function_call"] = {"name": "", "arguments": ""}
                name_ = getattr(c.delta.function_call, "name", None)
                if name_:
                    message["function_call"]["name"] += name_
                arguments_ = getattr(c.delta.function_call, "arguments", None)
                if arguments_:
                    message["function_call"]["arguments"] += arguments_
            if getattr(c.delta, "tool_calls", None):
                tool_calls_list = c.delta.tool_calls
                if tool_calls_list is not None:
                    for tool_call in tool_calls_list:
                        tool_calls[tool_call.index].append(tool_call)
    if tool_calls:
        message["tool_calls"] = [None for _ in range(max(tool_calls.keys()) + 1)]
        for index, tool_call_chunks in tool_calls.items():
            message["tool_calls"][index] = {
                "index": index,
                "id": next((c.id for c in tool_call_chunks if c.id), None),
                "type": next((c.type for c in tool_call_chunks if c.type), None),
                "function": {"name": "", "arguments": ""},
            }
            for chunk in tool_call_chunks:
                if getattr(chunk, "function", None):
                    name_ = getattr(chunk.function, "name", None)
                    if name_:
                        message["tool_calls"][index]["function"]["name"] += name_
                    arguments_ = getattr(chunk.function, "arguments", None)
                    if arguments_:
                        message["tool_calls"][index]["function"][
                            "arguments"
                        ] += arguments_
    return {
        "index": getattr(choices[0], "index", 0) if choices else 0,
        "finish_reason": next(
            (
                c.finish_reason
                for c in reversed_choices
                if getattr(c, "finish_reason", None)
            ),
            None,
        ),
        "message": message,
    }


def _process_response_iter_output(outputs: list[ResponseStreamEvent]) -> dict:
    for output in outputs:
        if output.type == "response.completed":
            return _process_responses_output(output.response)
    return {}


def _process_responses_output(response: Any) -> dict:
    if response:
        try:
            output = response.model_dump(exclude_none=True, mode="json")
            if usage := output.pop("usage", None):
                output["_inner_tokens_dict"] = _create_inner_tokens_dict(usage)
            return output
        except Exception:
            return {"output": response}
    return {}
