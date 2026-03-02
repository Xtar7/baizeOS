#!/usr/bin/env python3
# backend/tests/test_kb_api.py

import requests
import json
import time
import tempfile
from pathlib import Path

# 配置
BASE_URL = "http://localhost:5000"
KB_API = f"{BASE_URL}/v1/kb"
KB_UPLOAD_API = f"{BASE_URL}/v1/kb/upload"  # 文件上传路由
FILES_API = f"{BASE_URL}/v1/kb/files"

# 存储测试数据
test_data = {
    "kb_id": None,
    "kb_file_ids": []
}

def print_response(response, title):
    """打印响应信息"""
    print(f"\n{'=' * 60}")
    print(f"【{title}】")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"Response: {response.text}")
    print(f"{'=' * 60}")
    return response

def is_success(status_code):
    """判断请求是否成功（2xx）"""
    return 200 <= status_code < 300

def create_temp_file(content, suffix=".txt"):
    """创建临时文件（跨平台兼容）"""
    temp_dir = Path(tempfile.gettempdir())
    temp_file = temp_dir / f"test_{int(time.time())}{suffix}"  # 修复：移除 _{suffix.lstrip('.')}，避免双后缀如 _txt.txt
    temp_file.write_text(content, encoding='utf-8')
    return temp_file


def test_create_kb():
    """测试创建知识库"""
    print("\n>>> 测试创建知识库")

    payload = {
        "display_name": f"测试知识库_{int(time.time())}",
        "system_prompt": "你是一个专业的测试助手。",
        "description": "用于 API 测试的知识库"
    }

    response = requests.post(KB_API, json=payload)
    print_response(response, "创建知识库")

    if is_success(response.status_code):
        data = response.json()
        test_data["kb_id"] = data.get("kb_id")
        print(f"✅ 创建成功，kb_id: {test_data['kb_id']}")
        return True
    else:
        print("❌ 创建失败")
        return False


def test_list_kb():
    """测试列出所有知识库"""
    print("\n>>> 测试列出知识库")

    response = requests.get(f"{KB_API}/list")
    print_response(response, "列出知识库")

    if is_success(response.status_code):
        data = response.json()
        print(f"✅ 共 {data.get('total', 0)} 个知识库")
        return True
    else:
        print("❌ 获取失败")
        return False


def test_get_kb():
    """测试获取单个知识库"""
    if not test_data["kb_id"]:
        print("⚠️ 跳过：没有 kb_id")
        return False

    print(f"\n>>> 测试获取知识库: {test_data['kb_id']}")

    response = requests.get(f"{KB_API}/{test_data['kb_id']}")
    print_response(response, "获取知识库详情")

    if is_success(response.status_code):
        print("✅ 获取成功")
        return True
    else:
        print("❌ 获取失败")
        return False


def test_update_kb():
    """测试通用更新知识库"""
    if not test_data["kb_id"]:
        print("⚠️ 跳过：没有 kb_id")
        return False

    print(f"\n>>> 测试更新知识库: {test_data['kb_id']}")

    # 测试只改名称
    payload1 = {"display_name": f"修改后的名称_{int(time.time())}"}
    response = requests.put(f"{KB_API}/{test_data['kb_id']}", json=payload1)
    print_response(response, "更新名称")
    success1 = is_success(response.status_code)

    # 测试只改提示词
    payload2 = {"system_prompt": "这是更新后的系统提示词。"}
    response = requests.put(f"{KB_API}/{test_data['kb_id']}", json=payload2)
    print_response(response, "更新提示词")
    success2 = is_success(response.status_code)

    # 测试同时改多个字段
    payload3 = {
        "display_name": f"最终名称_{int(time.time())}",
        "system_prompt": "这是最终的系统提示词。",
        "description": "这是更新后的描述。"
    }
    response = requests.put(f"{KB_API}/{test_data['kb_id']}", json=payload3)
    print_response(response, "批量更新")
    success3 = is_success(response.status_code)

    return success1 and success2 and success3


def test_upload_file():
    """测试上传单个文件"""
    if not test_data["kb_id"]:
        print("⚠️ 跳过：没有 kb_id")
        return False

    print(f"\n>>> 测试上传文件到知识库: {test_data['kb_id']}")

    content = f"测试文件内容_{int(time.time())}"
    temp_file = create_temp_file(content, ".txt")
    filename = temp_file.name

    try:
        with open(temp_file, "rb") as f:
            files = {"file": (filename, f)}
            data = {"kb_id": test_data["kb_id"]}
            response = requests.post(KB_UPLOAD_API, files=files, data=data)
        print_response(response, "上传单个文件")

        if is_success(response.status_code):
            data = response.json()
            file_info = data.get("file_info")
            if file_info and "kb_file_id" in file_info:
                test_data["kb_file_ids"].append(file_info["kb_file_id"])
                print(f"✅ 上传成功，kb_file_id: {file_info['kb_file_id']}")
                return True
            else:
                print("❌ 响应缺少 file_info 或 kb_file_id")
                return False
        else:
            print("❌ 上传失败")
            return False
    finally:
        if temp_file.exists():
            temp_file.unlink()  # 添加：清理临时文件

# 类似微调 test_upload_multiple_files：添加 finally unlink

def test_upload_multiple_files():
    """测试上传多个文件"""
    if not test_data["kb_id"]:
        print("⚠️ 跳过：没有 kb_id")
        return False

    print(f"\n>>> 测试上传多个文件到知识库: {test_data['kb_id']}")

    success_count = 0
    temp_files = []
    for i in range(3):
        content = f"测试文件_{i}_{int(time.time())}"
        temp_file = create_temp_file(content, ".txt")
        temp_files.append(temp_file)
        filename = temp_file.name

        try:
            with open(temp_file, "rb") as f:
                files = {"file": (filename, f)}
                data = {"kb_id": test_data["kb_id"]}
                response = requests.post(KB_UPLOAD_API, files=files, data=data)
            print_response(response, f"上传文件 {i+1}")

            if is_success(response.status_code):
                data = response.json()
                file_info = data.get("file_info")
                if file_info and "kb_file_id" in file_info:
                    test_data["kb_file_ids"].append(file_info["kb_file_id"])
                    success_count += 1
        except Exception as e:
            print(f"❌ 上传文件 {i+1} 异常: {str(e)}")

    for tf in temp_files:
        if tf.exists():
            tf.unlink()  # 添加：清理所有临时文件

    if success_count == 3:
        print("✅ 所有文件上传成功")
        return True
    else:
        print(f"❌ {3 - success_count} 个文件上传失败")
        return False

def test_delete_single_file():
    """测试删除单个文件"""
    if not test_data["kb_id"] or not test_data["kb_file_ids"]:
        print("⚠️ 跳过：没有 kb_id 或 kb_file_id")
        return False

    kb_file_id = test_data["kb_file_ids"].pop(0)
    print(f"\n>>> 测试删除单个文件: {kb_file_id}")

    payload = {
        "kb_id": test_data["kb_id"],
        "kb_file_id": kb_file_id
    }

    response = requests.delete(FILES_API, json=payload)
    print_response(response, "删除单个文件")

    if is_success(response.status_code):
        print(f"✅ 删除成功，剩余文件: {len(test_data['kb_file_ids'])}")
        return True
    else:
        # 放回列表，以便后续清理
        test_data["kb_file_ids"].insert(0, kb_file_id)
        print("❌ 删除失败")
        return False


def test_delete_batch_files():
    """测试批量删除文件"""
    if not test_data["kb_id"] or len(test_data["kb_file_ids"]) < 2:
        print("⚠️ 跳过：文件数量不足")
        return False

    print(f"\n>>> 测试批量删除文件")

    # 取前两个文件批量删除
    batch_ids = test_data["kb_file_ids"][:2]

    payload = {
        "kb_id": test_data["kb_id"],
        "kb_file_ids": batch_ids
    }

    # 修复：批量删除也是 /v1/kb/files，不是 /v1/kb/files/batch
    response = requests.delete(FILES_API, json=payload)
    print_response(response, "批量删除文件")

    if is_success(response.status_code):
        test_data["kb_file_ids"] = test_data["kb_file_ids"][2:]
        print(f"✅ 批量删除成功，剩余文件: {len(test_data['kb_file_ids'])}")
        return True
    else:
        print("❌ 批量删除失败")
        return False


def test_delete_kb_by_body():
    """测试通过 Body 删除知识库"""
    if not test_data["kb_id"]:
        print("⚠️ 跳过：没有 kb_id")
        return False

    print(f"\n>>> 测试通过 Body 删除知识库: {test_data['kb_id']}")

    payload = {"kb_id": test_data["kb_id"]}

    response = requests.delete(KB_API, json=payload)
    print_response(response, "Body 删除知识库")

    if is_success(response.status_code):
        print("✅ 删除成功")
        test_data["kb_id"] = None
        return True
    else:
        print("❌ 删除失败")
        return False


def test_create_and_delete_batch():
    """测试创建并批量删除知识库"""
    print("\n>>> 测试批量删除知识库")

    # 创建多个测试知识库
    kb_ids = []
    for i in range(3):
        payload = {
            "display_name": f"批量测试_{i}_{int(time.time())}",
            "system_prompt": "测试用",
            "description": "用于批量删除测试"
        }
        response = requests.post(KB_API, json=payload)
        if is_success(response.status_code):
            kb_ids.append(response.json().get("kb_id"))

    print(f"创建了 {len(kb_ids)} 个测试知识库")

    if len(kb_ids) < 2:
        print("⚠️ 创建数量不足，跳过批量删除测试")
        return False

    # 批量删除
    payload = {"kb_ids": kb_ids}

    response = requests.delete(KB_API, json=payload)
    print_response(response, "批量删除知识库")

    if is_success(response.status_code):
        data = response.json()
        print(f"✅ 批量删除完成，成功: {data.get('deleted_count', 0)}，失败: {len(data.get('failed', []))}")
        return True

    return False


def cleanup():
    """清理测试数据"""
    print("\n>>> 清理测试数据")

    # 删除剩余的文件
    if test_data["kb_id"] and test_data["kb_file_ids"]:
        for kb_file_id in test_data["kb_file_ids"][:]:  # 复制列表避免修改时迭代问题
            payload = {
                "kb_id": test_data["kb_id"],
                "kb_file_id": kb_file_id
            }
            response = requests.delete(FILES_API, json=payload)
            if is_success(response.status_code):
                print(f"✅ 删除文件: {kb_file_id}")
                test_data["kb_file_ids"].remove(kb_file_id)  # 成功后移除
            else:
                print(f"❌ 删除文件失败: {kb_file_id}")
        print(f"清理了 {len(test_data['kb_file_ids'])} 个文件")  # 现在应为0

    # 删除知识库
    if test_data["kb_id"]:
        payload = {"kb_id": test_data["kb_id"]}
        response = requests.delete(KB_API, json=payload)
        if is_success(response.status_code):
            print(f"✅ 清理了知识库: {test_data['kb_id']}")
            test_data["kb_id"] = None
        else:
            print(f"❌ 清理知识库失败: {test_data['kb_id']}")

# ===============================
# RAG 验证模块
# ===============================

CHAT_API = f"{BASE_URL}/v1/chat/completions"

def ask_kb(question, kb_id):
    payload = {
        "model": "default",
        "messages": [
            {"role": "user", "content": question}
        ],
        "kb_id": kb_id
    }
    response = requests.post(CHAT_API, json=payload)
    if 200 <= response.status_code < 300:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print("请求失败:", response.text)
        return None


def test_rag_unique_hit():
    print("\n>>> 测试唯一知识命中")

    unique_content = "唯一标识：RAG-UNIQUE-998877"
    temp_file = create_temp_file(unique_content, ".txt")

    try:
        with open(temp_file, "rb") as f:
            files = {"file": (temp_file.name, f)}
            data = {"kb_id": test_data["kb_id"]}
            r = requests.post(KB_UPLOAD_API, files=files, data=data)

        if not is_success(r.status_code):  # 新增检查
            print(f"❌ 上传失败: {r.text}")
            return False

        time.sleep(5)  # 加长到 5 秒，测试是否延迟问题

        answer = ask_kb("唯一标识是什么？", test_data["kb_id"])
        print("模型回答：", answer)

        if "RAG-UNIQUE-998877" in answer:
            return True
        else:
            print("❌ RAG 未命中，检查服务器日志（retrieve_context 返回 []？）")
            return False

    finally:
        if temp_file.exists():
            temp_file.unlink()


def test_rag_delete_invalidation():
    print("\n>>> 测试删除后是否失效")

    content = "删除测试标识：DEL-112233"
    temp_file = create_temp_file(content, ".txt")

    try:
        with open(temp_file, "rb") as f:
            files = {"file": (temp_file.name, f)}
            data = {"kb_id": test_data["kb_id"]}
            r = requests.post(KB_UPLOAD_API, files=files, data=data)

        if not is_success(r.status_code):  # 新增：检查 status
            print(f"❌ 上传失败: status={r.status_code}, response={r.text}")
            return False

        try:
            data = r.json()
            file_info = data.get("file_info")  # 用 get 避免 KeyError
            if not file_info:
                print("❌ 响应缺少 file_info")
                return False
            kb_file_id = file_info["kb_file_id"]
        except Exception as e:
            print(f"❌ 解析响应失败: {str(e)}, response={r.text}")
            return False

        time.sleep(2)

        answer1 = ask_kb("删除测试标识是什么？", test_data["kb_id"])
        print("删除前回答:", answer1)

        requests.delete(FILES_API, json={
            "kb_id": test_data["kb_id"],
            "kb_file_id": kb_file_id
        })

        time.sleep(2)

        answer2 = ask_kb("删除测试标识是什么？", test_data["kb_id"])
        print("删除后回答:", answer2)

        return "DEL-112233" not in answer2

    finally:
        if temp_file.exists():
            temp_file.unlink()

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始 KB API 测试")
    print(f"Base URL: {BASE_URL}")
    print("=" * 60)

    tests = [
        ("创建知识库", test_create_kb),
        ("列出知识库", test_list_kb),
        ("获取知识库", test_get_kb),
        ("更新知识库", test_update_kb),
        ("上传文件", test_upload_file),
        ("上传多个文件", test_upload_multiple_files),
        ("RAG 唯一命中测试", test_rag_unique_hit),
        ("RAG 删除失效测试", test_rag_delete_invalidation),
        ("删除单个文件", test_delete_single_file),
        ("批量删除文件", test_delete_batch_files),
        ("Body 删除知识库", test_delete_kb_by_body),
        ("批量删除知识库测试", test_create_and_delete_batch),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "✅ 通过" if success else "❌ 失败"))
        except Exception as e:
            print(f"\n💥 {name} 异常: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((name, f"💥 异常: {str(e)}"))

    # 清理
    cleanup()

    # 打印测试报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    for name, result in results:
        print(f"{name}: {result}")
    print("=" * 60)

    passed = sum(1 for _, r in results if "通过" in r)
    total = len(results)
    print(f"总计: {passed}/{total} 通过")


if __name__ == "__main__":
    run_all_tests()