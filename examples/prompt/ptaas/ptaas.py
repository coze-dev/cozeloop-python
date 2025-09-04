# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
PTaaS Basic Example - Sync non-stream, sync stream, async non-stream, async stream calls

Demonstrates:
- Sync non-stream call
- Sync stream call
- Async non-stream call  
- Async stream call
"""

import asyncio
import os

from cozeloop import new_client, Client
from cozeloop.entities.prompt import Message, Role, ExecuteResult


def setup_client() -> Client:
    """
    Unified client setup function
    
    Environment variables:
    - COZELOOP_WORKSPACE_ID: workspace ID
    - COZELOOP_API_TOKEN: API token
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


def sync_non_stream_example(client: Client) -> None:
    """Sync non-stream call example"""
    print("=== Sync Non-Stream Example ===")
    
    # 1. Create a prompt on the platform
    # Create a Prompt on the platform's Prompt development page (set Prompt Key to 'ptaas_demo'),
    # add the following messages to the template, submit a version.
    # System: You are a helpful assistant for {{topic}}.
    # User: Please help me with {{user_request}}
    
    result = client.execute_prompt(
        prompt_key="ptaas_demo",
        version="0.0.1",
        variable_vals={
            "topic": "artificial intelligence",
            "user_request": "explain what is machine learning"
        },
        # You can also append messages to the prompt.
        messages=[
            Message(role=Role.USER, content="Keep the answer brief.")
        ],
        stream=False
    )
    print_execute_result(result)


def sync_stream_example(client: Client) -> None:
    """Sync stream call example"""
    print("=== Sync Stream Example ===")
    
    stream_reader = client.execute_prompt(
        prompt_key="ptaas_demo",
        version="0.0.1",
        variable_vals={
            "topic": "artificial intelligence",
            "user_request": "explain what is machine learning"
        },
        messages=[
            Message(role=Role.USER, content="Keep the answer brief.")
        ],
        stream=True
    )
    
    for result in stream_reader:
        print_execute_result(result)
    
    print("\nStream finished.")


async def async_non_stream_example(client: Client) -> None:
    """Async non-stream call example"""
    print("=== Async Non-Stream Example ===")
    
    result = await client.aexecute_prompt(
        prompt_key="ptaas_demo",
        version="0.0.1",
        variable_vals={
            "topic": "artificial intelligence",
            "user_request": "explain what is machine learning"
        },
        messages=[
            Message(role=Role.USER, content="Keep the answer brief.")
        ],
        stream=False
    )
    print_execute_result(result)


async def async_stream_example(client: Client) -> None:
    """Async stream call example"""
    print("=== Async Stream Example ===")
    
    stream_reader = await client.aexecute_prompt(
        prompt_key="ptaas_demo",
        version="0.0.1",
        variable_vals={
            "topic": "artificial intelligence",
            "user_request": "explain what is machine learning"
        },
        messages=[
            Message(role=Role.USER, content="Keep the answer brief.")
        ],
        stream=True
    )
    
    async for result in stream_reader:
        print_execute_result(result)
    
    print("\nStream finished.")


async def main():
    """Main function"""
    client = setup_client()
    
    try:
        # Sync non-stream call
        sync_non_stream_example(client)
        
        # Sync stream call
        sync_stream_example(client)
        
        # Async non-stream call
        await async_non_stream_example(client)
        
        # Async stream call
        await async_stream_example(client)
        
    finally:
        # Close client
        if hasattr(client, 'close'):
            client.close()


if __name__ == "__main__":
    asyncio.run(main())