# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os
import time

from langchain.callbacks.tracers import ConsoleCallbackHandler
from langchain_core.runnables import RunnableConfig
from langchain_openai import AzureChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from cozeloop import set_log_level
from cozeloop.integration.langchain.trace_callback import LoopTracer

logger = logging.getLogger(__name__)

def do_lcel_stream_demo():
    # Configure the parameters for the llm. The keys in os.environ are standard keys for Langchain and must be
    # followed. This is just a demo, and the connectivity of the llm needs to be ensured by the user.
    # os.environ['AZURE_OPENAI_API_KEY'] = 'xxx'  # need set a llm api key
    # os.environ['OPENAI_API_VERSION'] = '2024-05-13'  # llm version, see more: https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#rest-api-versioning
    # os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://xxx'  # llm endpoint
    # os.environ['AUZURE_DEPLOYMENT'] = 'gpt-4o-2024-05-13'

    # Configure the Loop environment variables. This is just a demo, and the keys in os.environ are not for reference.
    # The specific implementation method is determined by the business side.

    # Set the following environment variables first (Assuming you are using a PAT token.).
    # COZELOOP_WORKSPACE_ID=your workspace id
    # COZELOOP_API_TOKEN=your token
    # os.environ['COZELOOP_API_TOKEN'] = 'your token'
    # os.environ['COZELOOP_WORKSPACE_ID'] = 'your workspace'

    trace_callback_handler = LoopTracer.get_callback_handler()
    # init llm model
    llm_model = AzureChatOpenAI(azure_deployment=os.environ['AUZURE_DEPLOYMENT'])

    # execute lcel, and print intermediate results.
    lcel_sequence = llm_model | StrOutputParser()
    chunks = []
    for chunk in lcel_sequence.stream(
            input='用你所学的技巧，帮我生成几个有意思的问题',
            config=RunnableConfig(callbacks=[trace_callback_handler])
    ):
        chunks.append(chunk)
        print(chunk, end='', flush=True)

    time.sleep(5) # async report, so sleep wait for report finish
    print('\n====== model output start ======\n' + ''.join(chunks) + '\n====== model output finish ======\n')


if __name__ == "__main__":
    set_log_level(logging.INFO)
    do_lcel_stream_demo()