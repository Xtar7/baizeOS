#!/usr/bin/env python3
# backend/tests/test_tmp_api.py

import requests
import json
import time
import tempfile
from pathlib import Path
import os

# 配置
BASE_URL = "http://localhost:5000"
TMP_UPLOAD_API = f"{BASE_URL}/v1/files/upload"
TMP_LIST_API   = f"{BASE_URL}/v1/files/list"
TMP_DELETE_API = f"{BASE_URL}/v1/files/delete"

# 测试用 chat_id（可以固定，也可以随机生成）
TEST_CHAT_ID = f"test_chat_{int(time.time())}"

# 存储测试产生的临时文件ID（用于后续删除测试）
test_tmp_file_ids = []


def print_response(response, title):
    """打印响应信息"""
    print(f"\n{'=' * 70}")
    print(f"【{title}】")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except:
        print(f"Response: {response.text}")
    print(f"{'=' * 70}\n")
    return response


def is_success(status_code):
    return 200 <= status_code < 300


def create_temp_file(content: str, suffix=".txt"):
    """创建临时文件"""
    temp_dir = Path(tempfile.gettempdir())
    filename = f"tmp_test_{int(time.time() * 1000)}{suffix}"
    temp_file = temp_dir / filename
    temp_file.write_text(content, encoding="utf-8")
    return temp_file


def test_upload_single_file():
    """测试上传单个临时文件"""
    print(f"\n>>> 测试上传单个临时文件 (chat_id: {TEST_CHAT_ID})")

    content = f"这是单个临时文件测试内容 - {int(time.time())}"
    temp_file = create_temp_file(content)

    try:
        with open(temp_file, "rb") as f:
            files = {"file": (temp_file.name, f)}
            data = {"chat_id": TEST_CHAT_ID}
            response = requests.post(TMP_UPLOAD_API, files=files, data=data)

        print_response(response, "上传单个临时文件")

        if is_success(response.status_code):
            result = response.json()
            file_info = result.get("file", {})
            tmp_file_id = file_info.get("tmp_file_id")
            if tmp_file_id:
                test_tmp_file_ids.append(tmp_file_id)
                print(f"✅ 上传成功，tmp_file_id: {tmp_file_id}")
                return True
            else:
                print("❌ 响应中缺少 tmp_file_id")
                return False
        else:
            print("❌ 上传失败")
            return False

    finally:
        if temp_file.exists():
            temp_file.unlink()


def test_upload_multiple_files(count=3):
    """测试上传多个临时文件"""
    print(f"\n>>> 测试上传 {count} 个临时文件 (chat_id: {TEST_CHAT_ID})")

    success_count = 0
    temp_files = []

    for i in range(count):
        content = f"批量临时文件 {i+1} - {int(time.time())}"
        temp_file = create_temp_file(content)
        temp_files.append(temp_file)

        try:
            with open(temp_file, "rb") as f:
                files = {"file": (temp_file.name, f)}
                data = {"chat_id": TEST_CHAT_ID}
                response = requests.post(TMP_UPLOAD_API, files=files, data=data)

            print_response(response, f"上传文件 {i+1}/{count}")

            if is_success(response.status_code):
                result = response.json()
                file_info = result.get("file", {})
                tmp_file_id = file_info.get("tmp_file_id")
                if tmp_file_id:
                    test_tmp_file_ids.append(tmp_file_id)
                    success_count += 1
        except Exception as e:
            print(f"上传第 {i+1} 个文件时异常: {e}")

    # 清理临时文件
    for tf in temp_files:
        if tf.exists():
            tf.unlink()

    if success_count == count:
        print(f"✅ 全部 {count} 个文件上传成功")
        return True
    else:
        print(f"❌ 只有 {success_count}/{count} 个文件上传成功")
        return False


def test_list_tmp_files():
    """测试列出临时文件"""
    print(f"\n>>> 测试列出临时文件 (chat_id: {TEST_CHAT_ID})")

    payload = {"chat_id": TEST_CHAT_ID}
    response = requests.post(TMP_LIST_API, json=payload)

    print_response(response, "列出临时文件")

    if is_success(response.status_code):
        data = response.json()
        total = data.get("total", 0)
        files = data.get("data", [])
        print(f"找到 {total} 个临时文件")
        if files:
            print("前几个文件示例：")
            for f in files[:3]:
                print(f"  - {f.get('filename')} ({f.get('bytes')} bytes) id={f.get('tmp_file_id')}")
        return total > 0
    else:
        print("❌ 列出失败")
        return False


def test_delete_single_file():
    """测试删除单个临时文件"""
    if not test_tmp_file_ids:
        print("⚠️ 没有可删除的 tmp_file_id，跳过单个删除测试")
        return False

    tmp_id = test_tmp_file_ids.pop(0)  # 取第一个
    print(f"\n>>> 测试删除单个文件: {tmp_id} (chat_id: {TEST_CHAT_ID})")

    payload = {
        "chat_id": TEST_CHAT_ID,
        "tmp_file_id": tmp_id
    }
    response = requests.post(TMP_DELETE_API, json=payload)

    print_response(response, "删除单个临时文件")

    if is_success(response.status_code):
        data = response.json()
        deleted_count = data.get("deleted_count", 0)
        print(f"✅ 删除成功，deleted_count: {deleted_count}")
        return deleted_count > 0
    else:
        print("❌ 删除失败")
        return False


def test_delete_batch_files():
    """测试批量删除临时文件"""
    if len(test_tmp_file_ids) < 2:
        print("⚠️ 文件数量不足 2 个，跳过批量删除测试")
        return False

    to_delete = test_tmp_file_ids[:2]  # 取前两个
    test_tmp_file_ids[:] = test_tmp_file_ids[2:]  # 移除已测试的

    print(f"\n>>> 测试批量删除 {len(to_delete)} 个文件 (chat_id: {TEST_CHAT_ID})")
    print(f"待删除 IDs: {to_delete}")

    payload = {
        "chat_id": TEST_CHAT_ID,
        "tmp_file_ids": to_delete
    }
    response = requests.post(TMP_DELETE_API, json=payload)

    print_response(response, "批量删除临时文件")

    if is_success(response.status_code):
        data = response.json()
        deleted_count = data.get("deleted_count", 0)
        print(f"✅ 批量删除成功，deleted_count: {deleted_count}")
        return deleted_count == len(to_delete)
    else:
        print("❌ 批量删除失败")
        return False


def cleanup():
    """尝试清理剩余测试文件（防御性清理）"""
    print("\n>>> 清理剩余测试临时文件")

    if not test_tmp_file_ids:
        print("没有剩余文件需要清理")
        return

    payload = {
        "chat_id": TEST_CHAT_ID,
        "tmp_file_ids": test_tmp_file_ids[:]
    }
    response = requests.post(TMP_DELETE_API, json=payload)

    if is_success(response.status_code):
        data = response.json()
        count = data.get("deleted_count", 0)
        print(f"清理成功，删除了 {count} 个剩余文件")
        test_tmp_file_ids.clear()
    else:
        print("清理失败，可能文件已被删除或 chat_id 不匹配")


def run_all_tests():
    print("=" * 70)
    print("开始 TMP API 测试")
    print(f"Base URL: {BASE_URL}")
    print(f"Test chat_id: {TEST_CHAT_ID}")
    print("=" * 70)

    tests = [
        ("上传单个文件", test_upload_single_file),
        ("上传多个文件", lambda: test_upload_multiple_files(3)),
        ("列出临时文件", test_list_tmp_files),
        ("删除单个文件", test_delete_single_file),
        ("批量删除文件", test_delete_batch_files),
    ]

    results = []
    for name, func in tests:
        try:
            success = func()
            results.append((name, "通过" if success else "失败"))
        except Exception as e:
            print(f"\n💥 {name} 执行异常: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((name, f"异常: {str(e)}"))

    cleanup()

    print("\n" + "=" * 70)
    print("测试报告")
    print("=" * 70)
    for name, result in results:
        print(f"{name}: {result}")
    print("=" * 70)

    passed = sum(1 for _, r in results if "通过" in r)
    total = len(results)
    print(f"总计: {passed}/{total} 通过")


if __name__ == "__main__":
    run_all_tests()