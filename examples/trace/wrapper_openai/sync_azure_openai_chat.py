from openai import AzureOpenAI

from cozeloop import new_client
from cozeloop.decorator import observe
from cozeloop.integration.wrapper import openai_wrapper

openai_client = openai_wrapper(AzureOpenAI(
    # azure_endpoint="***",
    api_key="***",
    azure_deployment="gpt-5-chat-2025-08-07",
    api_version="",
))


def retriever():
    results = ["John worked at Beijing"]
    return results

@observe
def rag(question):
    docs = retriever()
    system_message = """Answer the question using only the provided information below:

    {docs}""".format(docs="\n".join(docs))

    # not stream
    res = openai_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": question},
        ],
        model="",
    )
    print(res)

    # stream
    # res = openai_client.chat.completions.create(
    #     messages=[
    #         {"role": "system", "content": system_message},
    #         {"role": "user", "content": question},
    #     ],
    #     model="",
    #     stream=True,
    #     extra_body={
    #         "stream_options": {
    #             "include_usage": True # bytedance gpt, return usage by this param
    #         }
    #     }
    # )
    # for chunk in res:
    #     print(chunk)


if __name__ == '__main__':
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # os.environ["COZELOOP_WORKSPACE_ID"] = "your workspace id"
    # os.environ["COZELOOP_API_TOKEN"] = "your token"

    client = new_client()
    rag("Where is John worked?")
    client.flush()
