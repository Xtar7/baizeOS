import requests
import json

BASE = "http://127.0.0.1:5000"


def test_models():
    print("\n=== 测试 models ===")
    r = requests.get(f"{BASE}/v1/models")
    print(r.status_code)
    print(r.text)


def test_chat():
    print("\n=== 测试普通对话 ===")
    payload = {
        "model": None,
        "messages": [
            {"role": "user", "content": "2+3等于多少"}
        ]
    }

    r = requests.post(
        f"{BASE}/v1/chat/completions",
        json=payload
    )
    print(r.status_code)
    print(r.text)


def test_rag_chat():
    print("\n=== 测试 RAG 对话 ===")
    payload = {
        "rag": True,
        "kb_id": "default",
        "messages": [
            {"role": "user", "content": "知识库里有什么内容？"}
        ]
    }

    r = requests.post(
        f"{BASE}/v1/chat/completions",
        json=payload
    )
    print(r.status_code)
    print(r.text)


if __name__ == "__main__":
    test_models()
    test_chat()
    test_rag_chat()
