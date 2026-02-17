from llama_cpp import Llama

llm = Llama(
    model_path=r"E:\baizeOS\models\llm\qwen2.5-7b-instruct-q5_k_m.gguf",
    n_ctx=4096
)

output = llm(
    "你好，介绍一下你自己",
    max_tokens=200
)

print(output["choices"][0]["text"])