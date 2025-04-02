# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import cozeloop

if __name__ == '__main__':
    """
    A simple example about how to handle loop sdk errors.
    """
    # Set the following environment variables first.
    # os.environ["COZELOOP_WORKSPACE_ID"] = "your workspace id"
    # os.environ["COZELOOP_JWT_OAUTH_CLIENT_ID"] = "your client id"
    # os.environ["COZELOOP_JWT_OAUTH_PRIVATE_KEY"] = "your private key"
    # os.environ["COZELOOP_JWT_OAUTH_PUBLIC_KEY_ID"] = "your public key id"

    # If you try to get an invalid prompt, you will get a LoopError.
    try:
        prompt = cozeloop.get_prompt("invalid key")
    except cozeloop.RemoteServiceError as e:
        # Loop sdk will always raise an exception which implement LoopError.
        # You can catch specific error to get more information.
        print(f"Got a loop error: error_code: {e.error_code}, log_id: {e.log_id}")

    # Considering that tracing is generally not in your main process, in order to simplify the business code,
    # all trace api will never return errors or throw panic. Therefore, the business does not need to handle exceptions.
    span = cozeloop.start_span("invalid name", "invalid type")
    span.finish()

    # Remember to close the client when program exits. If client is not closed, traces may be lost.
    cozeloop.close()
