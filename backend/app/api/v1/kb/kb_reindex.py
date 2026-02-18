# backend/app/api/v1/kb/kb_reindex.py
import logging
from flask import Blueprint, jsonify, request
from pathlib import Path

from app.services.kb_service import kb_service
from app.services.rag_service import rag_service
from app.services.upload_service import upload_service  # 用于重新 parse 文件
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

kb_reindex_bp = Blueprint("kb_reindex", __name__, url_prefix="/v1/kb")


@kb_reindex_bp.route("/<kb_id>/reindex", methods=["POST"])
def reindex_kb(kb_id):
    """
    重新索引知识库的所有文件向量
    POST /v1/kb/<kb_id>/reindex
    Body 可选：
      {"force": true}  # 强制重建，即使模型没变

    返回：
      - 成功：{"status": "completed", "ingested_files": N, "chunks": M}
      - 进行中/异步时可返回 "started"
    """
    data = request.get_json(silent=True) or {}
    force = data.get("force", False)

    try:
        meta = kb_service.get(kb_id)
        if not meta:
            return jsonify({"error": "知识库不存在"}), 404

        files = meta.get("files", [])
        if not files:
            return jsonify({
                "status": "completed",
                "message": "知识库中没有文件，无需重建",
                "ingested_files": 0,
                "chunks": 0
            }), 200

        logger.info(f"开始重建知识库 {kb_id} 的向量，文件数: {len(files)}，force={force}")

        # 获取当前目标模型
        target_model = meta.get("embedding_model", "bge-small-zh-v1.5")
        embedding_svc = get_embedding_service(target_model)
        actual_dim = embedding_svc.dim

        # 可选：如果不强制，且模型/维度没变，直接返回
        if not force:
            if target_model == meta.get("last_embedding_model") and actual_dim == meta.get("last_embedding_dim"):
                return jsonify({
                    "status": "skipped",
                    "message": "当前模型和维度与上次一致，无需重建",
                    "ingested_files": 0,
                    "chunks": 0
                }), 200

        # 先清空旧 index（最简单粗暴的方式，避免维度冲突或旧数据残留）
        vector_dir = Path(kb_service._kb_path(kb_id)) / "vector_store"
        if vector_dir.exists():
            for file in vector_dir.glob("*"):
                try:
                    file.unlink()
                except Exception as e:
                    logger.warning(f"删除旧向量文件失败: {file} - {e}")
        vector_dir.mkdir(parents=True, exist_ok=True)

        total_chunks = 0
        success_files = 0

        for file_info in files:
            relative_path = file_info["path"].lstrip("/")
            from app.config.settings import PROJECT_ROOT
            file_path = Path(PROJECT_ROOT) / relative_path

            if not file_path.exists():
                logger.warning(f"文件不存在，跳过: {file_path}")
                continue

            try:
                # 重新解析文件
                text = upload_service.parser.parse(file_path)
                if not text.strip():
                    logger.warning(f"文件内容为空，跳过: {file_path}")
                    continue

                # ingest（会自动 chunk、embed、add）
                result = rag_service.ingest_text(text, kb_id)
                total_chunks += result.get("chunks", 0)
                success_files += 1

                logger.debug(f"重建文件成功: {file_info['filename']}，chunks: {result.get('chunks', 0)}")

            except Exception as e:
                logger.error(f"重建文件失败 {file_info['filename']}: {str(e)}")
                # 可以选择 continue 或 raise，根据需求

        # 重建完成，更新 last_
        kb_service.update_last_embedding_info(kb_id, target_model, actual_dim)

        logger.info(f"知识库 {kb_id} 向量重建完成：{success_files}/{len(files)} 文件，{total_chunks} chunks")

        return jsonify({
            "status": "completed",
            "message": "向量重建成功",
            "ingested_files": success_files,
            "total_files": len(files),
            "chunks": total_chunks,
            "model_used": target_model,
            "dim": actual_dim
        }), 200

    except Exception as e:
        logger.exception(f"知识库 {kb_id} 重建失败")
        return jsonify({"error": f"重建失败: {str(e)}"}), 500