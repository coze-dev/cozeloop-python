# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging
import os

from langchain.callbacks.tracers import ConsoleCallbackHandler
from langchain_core.runnables import RunnableConfig
from langchain_openai import AzureChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from cozeloop import set_log_level
from cozeloop.integration.langchain.trace_callback import LoopTracer

logger = logging.getLogger(__name__)

def do_lcel_demo():
    # Configure the parameters for the large model. The keys in os.environ are standard keys for Langchain and must be
    # followed. This is just a demo, and the connectivity of the large model needs to be ensured by the user.
    os.environ['AZURE_OPENAI_API_KEY'] = 'xxx'  # need set a llm api key
    os.environ['OPENAI_API_VERSION'] = '2024-05-13'  # llm version, see more: https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#rest-api-versioning
    os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://xxx'  # llm endpoint
    os.environ['AUZURE_DEPLOYMENT'] = 'gpt-4o-2024-05-13'

    # Configure the Loop environment variables. This is just a demo, and the keys in os.environ are not for reference.
    # The specific implementation method is determined by the business side.
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # COZELOOP_WORKSPACE_ID=your workspace id
    # COZELOOP_API_TOKEN=your token
    os.environ['COZELOOP_API_TOKEN'] = 'your token'
    os.environ['COZELOOP_WORKSPACE_ID'] = 'your workspace'

    trace_callback_handler = LoopTracer.get_callback_handler()
    # init llm model
    llm_model = AzureChatOpenAI(azure_deployment=os.environ['AUZURE_DEPLOYMENT'])

    # execute lcel, and print intermediate results.
    lcel_sequence = llm_model | StrOutputParser()
    output = lcel_sequence.invoke(
        input='用你所学的技巧，帮我生成几个有意思的问题',
        config=RunnableConfig(callbacks=[ConsoleCallbackHandler(), trace_callback_handler])
    )
    print('\n====== model output start ======\n' + output + '\n====== model output finish ======\n')


if __name__ == "__main__":
    set_log_level(logging.INFO)
    do_lcel_demo()