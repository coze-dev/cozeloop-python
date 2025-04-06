# CozeLoop Python SDK
English | [简体中文](README.zh_CN.md)

## Overview

The CozeLoop SDK is a Python client for interacting with [CozeLoop platform](https://loop.coze.cn).
Key features:
- Report trace
- Get and format prompt

## Requirements
- Python 3.8 or higher

## Installation

`pip install CozeLoop`

## Usage

### Initialize

To get started, visit https://www.coze.cn/open/oauth/apps and create an OAuth app.
Then you can get your owner appid, public key and private key.

Set your environment variables:
```bash
export COZELOOP_WORKSPACE_ID=your workspace id
export COZELOOP_JWT_OAUTH_CLIENT_ID=your client id
export COZELOOP_JWT_OAUTH_PRIVATE_KEY=your private key
export COZELOOP_JWT_OAUTH_PUBLIC_KEY_ID=your public key id
```

### Report Trace

```python
def main():
    span = cozeloop.start_span("root", "custom")

    span.set_input("Hello") 
    span.set_output("World") 
	
    span.finish()
	
    cozeloop.close()
```

### Get Prompt
```python
def main():
    prompt = cozeloop.get_prompt(prompt_key="your_prompt_key")
    messages = cozeloop.prompt_format(
        prompt,
        {"var1": "your content"},
    )
```

You can see more examples [here](examples).

## Contribution

Please check [Contributing](CONTRIBUTING.md) for more details.

## Security

If you discover a potential security issue in this project, or think you may
have discovered a security issue, we ask that you notify Bytedance Security via our [security center](https://security.bytedance.com/src) or [vulnerability reporting email](sec@bytedance.com).

Please do **not** create a public GitHub issue.

## License

This project is licensed under the [MIT License](LICENSE).
