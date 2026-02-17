# backend/app/api/v1/kb/kb_update.py
from flask import Blueprint, request, jsonify
from app.services.kb_service import kb_service

kb_update_bp = Blueprint("kb_update", __name__, url_prefix="/v1/kb")


@kb_update_bp.route("/<kb_id>", methods=["PUT"])
def update_kb(kb_id):
    """
    通用更新：PUT /v1/kb/<kb_id>
    Body: 只传要改的字段
      {
        "display_name": "新名称",      // 可选
        "system_prompt": "新提示词",    // 可选
        "description": "新描述"         // 可选
      }

    流程：
    1. 前端先 GET /v1/kb/<kb_id> 获取完整数据
    2. 表单显示现有值
    3. 用户修改部分字段
    4. PUT 只传修改后的字段（或全部字段）
    5. 后端只更新提供的字段，未提供的保持原值
    """
    data = request.get_json(silent=True) or {}

    # 支持字段
    display_name = data.get("display_name")
    system_prompt = data.get("system_prompt")
    description = data.get("description")

    # 检查是否至少传了一个字段
    if all(v is None for v in [display_name, system_prompt, description]):
        return jsonify({"error": "至少需要一个更新字段（display_name, system_prompt, description）"}), 400

    try:
        meta = kb_service.update(
            kb_id,
            display_name=display_name,
            system_prompt=system_prompt,
            description=description
        )
        return jsonify(meta)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500