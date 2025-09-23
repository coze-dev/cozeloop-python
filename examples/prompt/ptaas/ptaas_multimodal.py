# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

"""
PTaaS Multimodal Example - Demonstrates image processing and multimodal input

Demonstrates:
- Image URL processing
- Base64 image data processing
- Multimodal message construction
"""

import os
import base64

from cozeloop import new_client, Client
from cozeloop.entities.prompt import Message, Role, ExecuteResult, ContentPart, ContentType


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


def multimodal_example(client: Client) -> None:
    """Multimodal example"""
    print("=== Multimodal Example ===")
    
    # 1. Create a prompt on the platform
    # Create a Prompt on the platform's Prompt development page (set Prompt Key to 'ptaas_demo'),
    # add the following messages to the template, submit a version. example1 and example2 are the multi modal variables.
    # System: You can quickly identify the location where a photo was taken.
    # User: For example: {{example1}}
    # Assistant: {{city1}}
    # User: For example: {{example2}}
    # Assistant: {{city2}}
    
    image_path = "your_image_path"
    # If image file exists, read and encode
    # If the image file exists, read and encode it
    if os.path.exists(image_path):
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
                base64_image = base64.b64encode(image_bytes).decode()
                base64_data = f"data:image/jpeg;base64,{base64_image}"
        except Exception as e:
            print(f"Warning: Could not read image file {image_path}: {e}")
            print("Using placeholder base64 data instead.")
    
    result = client.execute_prompt(
        prompt_key="ptaas_demo",
        version="0.0.8",
        # multi modal variable can be List[ContentPart]/ContentPart
        # Images can be provided via URL or in base64 encoded format.
        # Image URL needs to be publicly accessible.
        # Base64-formatted data should follow the standard data URI format, like "data:[<mediatype>][;base64],<data>".
        variable_vals={
            "example1": [
                ContentPart(
                    type=ContentType.IMAGE_URL,
                    image_url="https://p8.itc.cn/q_70/images03/20221219/61785c89cd17421ca0d007c7a87d09fb.jpeg"
                )
            ],
            "city1": "Beijing",
            "example2": [
                ContentPart(
                    type=ContentType.BASE64_DATA,
                    base64_data=base64_data
                )
            ],
            "city2": "Shanghai"
        },
        messages=[
            Message(
                role=Role.USER,
                parts=[
                    ContentPart(
                        type=ContentType.IMAGE_URL,
                        image_url="https://img0.baidu.com/it/u=1402951118,1660594928&fm=253&app=138&f=JPEG?w=800&h=1200"
                    ),
                    ContentPart(
                        type=ContentType.TEXT,
                        text="Where is this photo taken?"
                    )
                ]
            )
        ],
        stream=False
    )
    print_execute_result(result)


def main():
    """Main function"""
    # The explanation of multi modal is based on non-streaming execution, and it also applies to streaming execution.
    client = setup_client()
    
    try:
        multimodal_example(client)
    finally:
        # Close client
        if hasattr(client, 'close'):
            client.close()


if __name__ == "__main__":
    main()