# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
PTaaS Timeout Control Example - Demonstrates client timeout and context timeout control

Demonstrates:
- Client-level timeout settings
- Request-level timeout control
"""

import os

from cozeloop import new_client
from cozeloop.entities.prompt import ExecuteResult


def print_execute_result(result: ExecuteResult) -> None:
    """Unified result printing function, consistent with Go version format"""
    if result.message:
        print(f"Message: {result.message}")
    if result.finish_reason:
        print(f"FinishReason: {result.finish_reason}")
    if result.usage:
        print(f"Usage: {result.usage}")


def set_request_timeout():
    print("=== Request Timeout Example ===")
    
    # 1. Create a prompt on the platform
    # Create a Prompt on the platform's Prompt development page (set Prompt Key to 'ptaas_demo'),
    # add the following messages to the template, submit a version, and set a label (e.g., 'production') for that version.
    # System: You are a helpful assistant for {{topic}}.
    # User: Please help me with {{user_request}}
    
    # Set the following environment variables first.
    # COZELOOP_WORKSPACE_ID=your workspace id
    # COZELOOP_API_TOKEN=your token
    client = new_client(
        api_base_url=os.getenv("COZELOOP_API_BASE_URL"),
        workspace_id=os.getenv("COZELOOP_WORKSPACE_ID"),
        api_token=os.getenv("COZELOOP_API_TOKEN"),
    )

    result = client.execute_prompt(
        prompt_key="ptaas_demo",
        version="0.0.1",
        variable_vals={
            "topic": "artificial intelligence",
            "user_request": "explain what is machine learning"
        },
        stream=False,
        timeout=1  # Set request timeout, default is 600s, max is 600s.
    )
    print_execute_result(result)


def main():
    """Main function"""
    # The explanation of timeout settings is based on non-streaming execution, and it also applies to streaming execution.
    set_request_timeout()


if __name__ == "__main__":
    main()