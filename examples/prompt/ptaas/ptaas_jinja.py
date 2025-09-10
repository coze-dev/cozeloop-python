# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
PTaaS Jinja2 Template Example - Demonstrates the use of complex variable structures

Demonstrates:
- Jinja2 template syntax
- Usage of complex object variables
"""

import os
from typing import Dict, Any

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


def jinja_template_example(client: Client) -> None:
    """Jinja2 template example"""
    print("=== Jinja2 Template Example ===")
    
    # 1. Create a prompt using jinja2 template on the platform
    # Create a Prompt on the platform's Prompt development page (set Prompt Key to 'ptaas_demo'),
    # add the following messages to the template, submit a version, and set a label (e.g., 'production') for that version.
    # System: You are a helpful assistant for {{param.topic}}. Your audience is {{param.age}} years old.
    # User: Please help me with {{param.user_request}}
    
    result = client.execute_prompt(
        prompt_key="ptaas_demo",
        version="0.0.2",
        variable_vals={
            "param": {
                "topic": "artificial intelligence",
                "age": 10,
                "user_request": "explain what is machine learning"
            }
        },
        stream=False
    )
    print_execute_result(result)


def main():
    """Main function"""
    # The explanation of jinja2 template is based on non-streaming execution, and it also applies to streaming execution.
    client = setup_client()
    
    try:
        jinja_template_example(client)
    finally:
        # Close client
        if hasattr(client, 'close'):
            client.close()


if __name__ == "__main__":
    main()