#!/usr/bin/env python3
# backend/tests/test_kb_full.py
# 测试知识库完整流程，包括 embedding 模型切换和 reindex

import requests
import json
import time
import tempfile
from pathlib import Path

# 配置
BASE_URL = "http://localhost:5000"
KB_API = f"{BASE_URL}/v1/kb"
KB_UPLOAD_API = f"{BASE_URL}/v1/kb/upload"
FILES_API = f"{BASE_URL}/v1/kb/files"           # 用于删除文件（可选）
REINDEX_API = f"{BASE_URL}/v1/kb"               # + /<kb_id>/reindex
MODELS_API = f"{BASE_URL}/v1/rag/embedding/models"  # 如果你加了这个接口

# 测试数据存储
test_data = {
    "kb_id": None,
    "kb_file_ids": [],
    "original_model": None,
    "new_model": "bge-base-zh-v1.5"  # 假设你要测试切换到这个模型（需先放好文件夹）
}

def print_response(response, title):
    print(f"\n{'=' * 80}")
    print(f"【{title}】")
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(response.text)
    print(f"{'=' * 80}\n")
    return response


def is_success(status_code):
    return 200 <= status_code < 300


def create_temp_file(content, suffix=".txt"):
    temp_dir = Path(tempfile.gettempdir())
    filename = f"test_kb_{int(time.time() * 1000)}{suffix}"
    temp_file = temp_dir / filename
    temp_file.write_text(content, encoding="utf-8")
    return temp_file


def test_create_kb():
    print("\n>>> 测试创建知识库")
    payload = {
        "display_name": f"测试 KB {int(time.time())}",
        "system_prompt": "你是一个专业的助手。",
        "description": "用于接口测试",
        "embedding_model": "bge-small-zh-v1.5"  # 指定初始模型
    }
    resp = requests.post(KB_API, json=payload)
    print_response(resp, "创建知识库")

    if is_success(resp.status_code):
        data = resp.json()
        test_data["kb_id"] = data.get("kb_id")
        test_data["original_model"] = data.get("embedding_model")
        print(f"创建成功，kb_id: {test_data['kb_id']}")
        return True
    return False


def test_get_models():
    if not MODELS_API:
        print("跳过：未配置模型列表接口")
        return False

    print("\n>>> 测试获取可用 embedding 模型列表")
    resp = requests.get(MODELS_API)
    print_response(resp, "获取 embedding 模型列表")

    if is_success(resp.status_code):
        data = resp.json()
        print(f"可用模型数量: {data.get('total')}")
        for m in data.get("models", [])[:3]:
            print(f"  - {m['name']} (dim: {m['dim']})")
        return True
    return False


def test_update_embedding_model():
    if not test_data["kb_id"]:
        print("跳过：没有 kb_id")
        return False

    print(f"\n>>> 测试更新 embedding_model 到 {test_data['new_model']}")
    payload = {
        "embedding_model": test_data["new_model"]
    }
    url = f"{KB_API}/{test_data['kb_id']}"
    resp = requests.put(url, json=payload)
    print_response(resp, "更新 embedding_model")

    if is_success(resp.status_code):
        data = resp.json()
        if data.get("needs_rebuild"):
            print("检测到需要重建向量！reason:", data.get("rebuild_reason"))
        else:
            print("无需重建（模型或 dim 未变化）")
        return data.get("needs_rebuild", False)
    return False


def test_upload_file():
    if not test_data["kb_id"]:
        print("跳过：没有 kb_id")
        return False

    print(f"\n>>> 测试上传文件到 KB {test_data['kb_id']}")
    content = f"测试内容 {int(time.time())} " * 50
    temp_file = create_temp_file(content)

    try:
        with open(temp_file, "rb") as f:
            files = {"file": (temp_file.name, f)}
            data = {"kb_id": test_data["kb_id"]}
            resp = requests.post(KB_UPLOAD_API, files=files, data=data)
        print_response(resp, "上传文件")

        if is_success(resp.status_code):
            file_info = resp.json().get("file_info", {})
            file_id = file_info.get("kb_file_id")
            if file_id:
                test_data["kb_file_ids"].append(file_id)
                print(f"上传成功，file_id: {file_id}")
                return True
    finally:
        if temp_file.exists():
            temp_file.unlink()

    return False


def test_reindex():
    if not test_data["kb_id"]:
        print("跳过：没有 kb_id")
        return False

    print(f"\n>>> 测试重新索引知识库 {test_data['kb_id']}")
    url = f"{REINDEX_API}/{test_data['kb_id']}/reindex"
    # 可选：加 force 参数强制重建
    payload = {"force": True}  # 测试时强制一次
    resp = requests.post(url, json=payload)
    print_response(resp, "重新索引")

    if is_success(resp.status_code):
        data = resp.json()
        print(f"重建完成：{data.get('ingested_files')} 文件，{data.get('chunks')} chunks")
        print(f"使用模型: {data.get('model_used')} (dim: {data.get('dim')})")
        return True
    return False


def test_list_kb():
    print("\n>>> 测试列出所有知识库")
    resp = requests.get(f"{KB_API}/list")
    print_response(resp, "列出知识库")

    if is_success(resp.status_code):
        data = resp.json()
        print(f"知识库总数: {data.get('total')}")
        return True
    return False


def test_get_kb():
    if not test_data["kb_id"]:
        print("跳过：没有 kb_id")
        return False

    print(f"\n>>> 测试获取单个 KB {test_data['kb_id']}")
    resp = requests.get(f"{KB_API}/{test_data['kb_id']}")
    print_response(resp, "获取单个知识库")

    if is_success(resp.status_code):
        data = resp.json()
        print(f"当前模型: {data.get('embedding_model')}")
        print(f"上次模型: {data.get('last_embedding_model')}")
        return True
    return False


def cleanup():
    print("\n>>> 清理测试数据")
    if test_data["kb_id"]:
        payload = {"kb_id": test_data["kb_id"]}
        resp = requests.delete(KB_API, json=payload)
        if is_success(resp.status_code):
            print(f"成功删除测试 KB: {test_data['kb_id']}")
        else:
            print("删除 KB 失败，可能已手动删除")
        test_data["kb_id"] = None
        test_data["kb_file_ids"] = []


def run_tests():
    print("=" * 80)
    print("开始 KB 接口完整测试")
    print(f"Base URL: {BASE_URL}")
    print("=" * 80)

    tests = [
        ("创建知识库", test_create_kb),
        ("获取可用 embedding 模型列表", test_get_models),
        ("更新 embedding_model 并检查重建提示", test_update_embedding_model),
        ("上传文件到 KB", test_upload_file),
        ("重新索引知识库", test_reindex),
        ("列出所有知识库", test_list_kb),
        ("获取单个 KB 详情", test_get_kb),
    ]

    results = []
    for name, func in tests:
        try:
            success = func()
            results.append((name, "通过" if success else "失败/跳过"))
        except Exception as e:
            print(f"测试 {name} 异常: {str(e)}")
            results.append((name, "异常"))

    cleanup()

    print("\n" + "=" * 80)
    print("测试报告")
    print("=" * 80)
    for name, result in results:
        print(f"{name}: {result}")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()