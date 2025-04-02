# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging

from cozeloop import new_client
from cozeloop.logger import set_log_level

logger = logging.getLogger(__name__)


def do_with_as_span_demo():
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # os.environ["COZELOOP_WORKSPACE_ID"] = "your workspace id"
    # os.environ["COZELOOP_API_TOKEN"] = "your token"

    # 1. new client
    set_log_level(logging.INFO)
    client = new_client()

    # 2. start span
    with client.start_span("span", "model") as span:
        # 3. set span or baggage
        # set custom tag
        span.set_tags({
            "mode": "simple",
            "node_id": 6076665,
            "node_process_duration": 228.6,
        })
        # set custom baggage, baggage can cover tag of sample key, and baggage will pass to child span automatically.
        span.set_baggage({
            "product_id": "123456654321",  # Assuming product_id is global field
        })

        # set tag key: `input`
        span.set_input('llm input')

        # set tag key: `output`
        span.set_output('llm output')

        # 4. span finish
        # When the 'with as' ends, finish() will be automatically executed, no need to manually call finish.

        with client.start_span("span1", "model") as span1:
            span1.set_tags({"node_name": "with_as_span1"})
            span1.finish()

    with client.start_span("span2", "model") as span2:
        span2.finish()

    # 4. (optional) flush or close
    # -- force flush, report all traces in the queue
    # Warning! In general, this method is not needed to be call, as spans will be automatically reported in batches.
    # Note that flush will block and wait for the report to complete, and it may cause frequent reporting,
    # affecting performance.
    client.flush()

    # -- close trace, do flush and close client
    # Warning! Once Close is executed, the client will become unavailable and a new client needs
    # to be created via NewClient! Use it only when you need to release resources, such as shutting down an instance!
    # client.close()


if __name__ == '__main__':
    do_with_as_span_demo()
