# backend/app/api/v1/kb/kb_list.py
from flask import Blueprint, jsonify
from app.services.kb_service import kb_service

kb_list_bp = Blueprint("kb_list", __name__, url_prefix="/v1/kb")


@kb_list_bp.route("/list", methods=["GET"])
def list_kb():
    """
    列出所有知识库，返回完整的 meta 信息（包含 id、display_name 等）
    """
    try:
        kbs = kb_service.list()

        # 可以选择只返回部分字段，减少响应体积
        simplified = [
            {
                "id": kb["id"],
                "display_name": kb["display_name"],
                "description": kb.get("description", ""),
                "created_at": kb["created_at"],
                "updated_at": kb["updated_at"],
                # 可选：加上文件数量等统计
                "file_count": len(kb.get("files", []))
            }
            for kb in kbs
        ]

        return jsonify({
            "object": "list",
            "data": simplified,
            "total": len(simplified)
        })
    except Exception as e:
        return jsonify({"error": f"获取列表失败: {str(e)}"}), 500