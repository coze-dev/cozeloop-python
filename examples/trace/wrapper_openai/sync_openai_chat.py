from openai import OpenAI

from cozeloop import new_client
from cozeloop.decorator import observe
from cozeloop.integration.wrapper import openai_wrapper

openai_client = openai_wrapper(OpenAI(
    base_url="https://ark.cn-beijing.volces.com/api/v3", # use ark model, refer: https://www.volcengine.com/docs/82379/1361424
    api_key="***",
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
    # res = openai_client.chat.completions.create(    # chat completion
    #     messages=[
    #         {"role": "system", "content": system_message},
    #         {"role": "user", "content": question},
    #     ],
    #     model="doubao-1-5-vision-pro-32k-250115",
    # )
    # print(res)

    # stream
    res = openai_client.chat.completions.create(  # chat completion
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": question},
        ],
        model="doubao-1-5-vision-pro-32k-250115",
        stream=True,
        extra_body={
            "stream_options": {
                "include_usage": True  # ark model, return token usage by this param
            }
        }
    )
    for chunk in res:
        print(chunk)


if __name__ == '__main__':
    # Set the following environment variables first (Assuming you are using a PAT token.).
    # os.environ["COZELOOP_WORKSPACE_ID"] = "your workspace id"
    # os.environ["COZELOOP_API_TOKEN"] = "your token"

    client = new_client()
    rag("Where is John worked?")
    client.flush()