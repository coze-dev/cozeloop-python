# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import sys

import cozeloop

if __name__ == '__main__':
    """
    A simple example about how to set logger and log level
    """
    # Set the following environment variables first.
    # os.environ["COZELOOP_WORKSPACE_ID"] = "your workspace id"
    # os.environ["COZELOOP_JWT_OAUTH_CLIENT_ID"] = "your client id"
    # os.environ["COZELOOP_JWT_OAUTH_PRIVATE_KEY"] = "your private key"
    # os.environ["COZELOOP_JWT_OAUTH_PUBLIC_KEY_ID"] = "your public key id"

    # You can set log level. Default log level is logging.WARNING
    cozeloop.set_log_level(logging.DEBUG)

    # You can add custom log handler and default handler will be removed.
    # Default log handler is stdout.
    custom_handler = logging.StreamHandler(sys.stdout)
    custom_handler.setFormatter(logging.Formatter('%(asctime)s %(name)s %(filename)s:%(lineno)d [Custom] [%(levelname)s] %(message)s'))
    cozeloop.add_log_handler(custom_handler)

    span = cozeloop.start_span("your span name", "custom")
    span.finish()

    # Remember to close the client when program exits. If client is not closed, traces may be lost.
    cozeloop.close()

