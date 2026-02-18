# backend/app/api/v1/kb/kb_update.py
import logging
from flask import Blueprint, request, jsonify
from app.services.kb_service import kb_service
from app.services.embedding_service import get_embedding_service  # ← 新增导入

logger = logging.getLogger(__name__)

kb_update_bp = Blueprint("kb_update", __name__, url_prefix="/v1/kb")


@kb_update_bp.route("/<kb_id>", methods=["PUT"])
def update_kb(kb_id):
    """
    通用更新：PUT /v1/kb/<kb_id>
    Body: 只传要改的字段
      {
        "display_name": "新名称",      // 可选
        "system_prompt": "新提示词",    // 可选
        "description": "新描述",         // 可选
        "embedding_model": "bge-base-zh-v1.5"  // 可选，切换模型
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
    embedding_model = data.get("embedding_model")

    # 检查是否至少传了一个字段
    if all(v is None for v in [display_name, system_prompt, description, embedding_model]):
        return jsonify({"error": "至少需要一个更新字段（display_name, system_prompt, description, embedding_model）"}), 400

    try:
        # 先获取当前 meta，用于对比
        current_meta = kb_service.get(kb_id)
        if not current_meta:
            return jsonify({"error": "知识库不存在"}), 404

        # 更新
        meta = kb_service.update(
            kb_id,
            display_name=display_name,
            system_prompt=system_prompt,
            description=description,
            embedding_model=embedding_model
        )

        # 如果切换了 embedding_model，检查是否需要重建
        needs_rebuild = False
        rebuild_reason = None

        if embedding_model and embedding_model != current_meta.get("last_embedding_model"):
            needs_rebuild = True
            rebuild_reason = f"embedding 模型从 {current_meta.get('last_embedding_model', '未设置')} 变更为 {embedding_model}"

        # 次要检查 dim（如果 meta 有 last_dim 和新 dim 不一致）
        new_dim = None
        try:
            svc = get_embedding_service(embedding_model or current_meta.get("embedding_model", "bge-small-zh-v1.5"))
            new_dim = svc.dim
            if new_dim != current_meta.get("last_embedding_dim"):
                needs_rebuild = True
                rebuild_reason = f"embedding 维度不一致（旧: {current_meta.get('last_embedding_dim')} → 新: {new_dim}），强制重建"
        except Exception as dim_err:
            logger.warning(f"获取新模型维度失败（不影响更新）: {str(dim_err)}")

        response_data = {
            "kb": meta,
            "updated": True,
            "needs_rebuild": needs_rebuild
        }

        if needs_rebuild:
            response_data["rebuild_reason"] = rebuild_reason
            response_data["message"] = "embedding 模型已更新，但向量索引需要重建。请调用重建接口或手动触发。"

        return jsonify(response_data), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.exception("更新知识库失败")
        return jsonify({"error": f"更新失败: {str(e)}"}), 500