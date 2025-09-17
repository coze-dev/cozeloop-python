import asyncio

from openai import AsyncOpenAI

from cozeloop import new_client
from cozeloop.decorator import observe
from cozeloop.integration.wrapper import openai_wrapper

openai_client = openai_wrapper(AsyncOpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3", # use ark model, refer: https://www.volcengine.com/docs/82379/1361424
    api_key="***",
))


def retriever():
    results = ["John worked at Beijing"]
    return results


@observe
async def rag(question):
    docs = retriever()
    system_message = """Answer the question using only the provided information below:

    {docs}""".format(docs="\n".join(docs))

    # not stream
    res = await openai_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": question},
        ],
        model="doubao-1-5-vision-pro-32k-250115",
    )
    print(res)

    # stream
    # res = await openai_client.chat.completions.create(
    #     messages=[
    #         {"role": "system", "content": system_message},
    #         {"role": "user", "content": question},
    #     ],
    #     model="doubao-1-5-vision-pro-32k-250115",
    #     stream=True,
    #     extra_body={
    #         "stream_options": {
    #             "include_usage": True  # bytedance gpt, return usage by this param
    #         }
    #     }
    # )
    # try:
    #     async for chunk in res:
    #         print(chunk)
    # except Exception as e:
    #     print(e)


if __name__ == '__main__':
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # os.environ["COZELOOP_WORKSPACE_ID"] = "your workspace id"
    # os.environ["COZELOOP_API_TOKEN"] = "your token"

    client = new_client()
    asyncio.run(rag("Where is John worked?"))
    client.flush()
