# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import logging

from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from cozeloop import set_log_level, new_client
from cozeloop.integration.langchain.trace_callback import LoopTracer

logger = logging.getLogger(__name__)

def do_lcel_demo():
    # Configure the parameters for the large model. The keys in os.environ are standard keys for Langchain and must be
    # followed. This is just a demo, and the connectivity of the large model needs to be ensured by the user.
    # os.environ['OPENAI_API_KEY'] = 'xxx'  # need set a openai key

    # Configure the CozeLoop environment variables. This is just a demo, and the keys in os.environ are not for reference.
    # The specific implementation method is determined by the business side.
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # os.environ['COZELOOP_API_TOKEN'] = 'your token'
    # os.environ['COZELOOP_WORKSPACE_ID'] = 'your workspace id'

    client = new_client()
    trace_callback_handler = LoopTracer.get_callback_handler(client)
    # init llm model
    llm_model = ChatOpenAI(model="doubao-1-5-vision-pro-32k-250115", base_url="https://ark.cn-beijing.volces.com/api/v3")

    # execute lcel, and print intermediate results.
    lcel_sequence = llm_model | StrOutputParser()
    output = lcel_sequence.invoke(
        input='用你所学的技巧，帮我生成几个有意思的问题',
        config=RunnableConfig(callbacks=[trace_callback_handler])
    )
    print('\n====== model output start ======\n' + output + '\n====== model output finish ======\n')
    client.close()


if __name__ == "__main__":
    set_log_level(logging.INFO)
    do_lcel_demo()