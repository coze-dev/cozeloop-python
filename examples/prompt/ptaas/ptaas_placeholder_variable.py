# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
PTaaS Placeholder Variable Example - Demonstrates the use of chat_history placeholder variables

Demonstrates:
- How to use placeholder variables
- Processing of chat_history variables
"""

import os
from typing import List

from cozeloop import new_client, Client
from cozeloop.entities.prompt import Message, Role, ExecuteResult


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


def placeholder_variable_example(client: Client) -> None:
    """Placeholder variable example"""
    print("=== Placeholder Variable Example ===")
    
    # 1. Create a prompt on the platform
    # Create a Prompt on the platform's Prompt development page (set Prompt Key to 'ptaas_demo'),
    # add the following messages to the template, submit a version.
    # System: You are a helpful assistant for {{topic}}.
    # Placeholder: {{chat_history}}
    # User: Please help me with {{user_request}}
    
    result = client.execute_prompt(
        prompt_key="ptaas_demo",
        version="0.0.5",
        variable_vals={
            "topic": "artificial intelligence",
            # chat_history is a placeholder variable, and it can be List[Message]/Message.
            "chat_history": [
                Message(role=Role.USER, content="hello"),
                Message(role=Role.ASSISTANT, content="hello")
            ],
            "user_request": "explain what is machine learning"
        },
        stream=False
    )
    print_execute_result(result)


def main():
    """Main function"""
    # The explanation of placeholder variable is based on non-streaming execution, and it also applies to streaming execution.
    client = setup_client()
    
    try:
        placeholder_variable_example(client)
    finally:
        # Close client
        if hasattr(client, 'close'):
            client.close()


if __name__ == "__main__":
    main()