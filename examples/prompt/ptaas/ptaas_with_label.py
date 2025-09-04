# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
PTaaS Label Usage Example - Demonstrates the use of label parameter

Demonstrates:
- How to use label parameter
- Version label management
"""

import os

from cozeloop import new_client, Client
from cozeloop.entities.prompt import ExecuteResult


def setup_client() -> Client:
    """
    Unified client setup function
    """
    # Set the following environment variables first.
    # COZELOOP_WORKSPACE_ID=your workspace id
    # COZELOOP_API_TOKEN=your token
    client = new_client(
        api_base_url=os.getenv("COZELOOP_API_BASE_URL"),
        workspace_id=os.getenv("COZELOOP_WORKSPACE_ID"),
        api_token=os.getenv("COZELOOP_API_TOKEN"),
    )
    return client


def print_execute_result(result: ExecuteResult) -> None:
    """Unified result printing function, consistent with Go version format"""
    if result.message:
        print(f"Message: {result.message}")
    if result.finish_reason:
        print(f"FinishReason: {result.finish_reason}")
    if result.usage:
        print(f"Usage: {result.usage}")


def label_example(client: Client) -> None:
    """Label usage example"""
    print("=== Label Example ===")
    
    # 1. Create a prompt on the platform
    # Create a Prompt on the platform's Prompt development page (set Prompt Key to 'ptaas_demo'),
    # add the following messages to the template, submit a version, and set a label (e.g., 'production') for that version.
    # System: You are a helpful assistant for {{topic}}.
    # User: Please help me with {{user_request}}
    
    result = client.execute_prompt(
        prompt_key="ptaas_demo",
        label="production",  # Note: When version is specified, label field will be ignored
        variable_vals={
            "topic": "artificial intelligence",
            "user_request": "explain what is machine learning"
        },
        stream=False
    )
    print_execute_result(result)


def main():
    """Main function"""
    # The explanation of label is based on non-streaming execution, and it also applies to streaming execution.
    client = setup_client()
    
    try:
        label_example(client)
    finally:
        # Close client
        if hasattr(client, 'close'):
            client.close()


if __name__ == "__main__":
    main()