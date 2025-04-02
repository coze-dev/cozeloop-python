# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import cozeloop


def use_new_client():
    # IMPORTANT: The client is thread-safe. You should NewClient only once in your program.
    client = cozeloop.new_client(
        # You can also set your token instead of environment variables.
        # api_token="your token",

        # You can set the workspace ID instead of environment variables.
        # workspace_id="your workspace id",

        # You can set the API base URL. Generally, there's no need to use it.
        # api_base_url="https://api.coze.cn",

        # The SDK will communicate with the Loop server. You can set the read timeout for requests.
        # Default value is 3 seconds.
        timeout=3,
        # The SDK will upload images or large text to file storage server when necessary.
        # You can set the upload timeout for requests.
        # Default value is 30 seconds.
        upload_timeout=30,
        # If your trace input or output is more than 1M, and UltraLargeTraceReport is false,
        # input or output will be cut off.
        # If UltraLargeTraceReport is true, input or output will be uploaded to file storage server separately.
        # Default value is false.
        ultra_large_report=False,
        # The SDK will cache the prompts locally. You can set the max count of prompts.
        # Default value is 100.
        prompt_cache_max_count=100,
        # The SDK will refresh the local prompts cache periodically. You can set the refresh interval.
        # Default value is 10 minutes.
        prompt_cache_refresh_interval=10 * 60,
        # Set whether to report a trace span when get or format prompt.
        # Default value is false.
        prompt_trace=False,
    )

    # Then you can call the functions in the client.
    span = client.start_span("first_span", "custom")
    span.finish()

    # Remember to close the client when program exits. If client is not closed, traces may be lost.
    client.close()


if __name__ == "__main__":
    """
    A simple example to init loop client by personal access token.

    First, you should access https://www.coze.cn/open/oauth/pat and create a new token.
    The specific process can be referred to the document: todo
    You should keep your publicKeyID and privateKey safe to prevent data leakage.
    """
    # Set the following environment variables first.
    # os.environ["COZELOOP_WORKSPACE_ID"] = "your workspace id"
    # os.environ["COZELOOP_API_TOKEN"] = "your token"

    # If you needn't any specific configs, you can call any functions without new a LoopClient.
    span = cozeloop.start_span("first_span", "custom")
    span.finish()

    # Remember to close the client when program exits. If client is not closed, traces may be lost.
    cozeloop.close()

    # Or you can call NewClient to init a LoopClient if you want to make more custom configs.
    # use_new_client()
