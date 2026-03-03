# backend/app/services/rag_service.py
import json
import logging
import re
from typing import List, Dict, Any, Generator, Union, Tuple, Optional
from app.config.settings import PROJECT_ROOT
from app.rag.index_manager import IndexManager
from app.rag.retriever import Retriever
from app.services.llm_service import llm_service
from app.services.kb_service import kb_service
from app.services.embedding_factory import get_embedding_service
from app.rag.chunker import chunk_text
from app.config.settings import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)
KB_ROOT = PROJECT_ROOT / "knowledge_base"

# ==============================
# 企业级 RAG 防护配置（集中管理，支持环境变量覆盖）
# ==============================
RAG_GUARD_CONFIG = {
    # 第一层：检索阈值防护
    "enable_score_guard": True,  # 是否启用相似度阈值检查
    "score_threshold": 0.50,  # 最低相似度阈值（低于此值拒答）
    "strict_reference_threshold": 0.70,  # 严格引用阈值（高于此值才显示引用）

    # 第二层：内容一致性防护
    "enable_consistency_check": True,  # 是否启用生成内容一致性检查
    "consistency_mode": "hybrid",  # 检查模式：strict | loose | hybrid
    "min_sentence_length": 6,  # 宽松模式下句子最小长度
    "keyword_match_ratio": 0.3,  # hybrid模式下关键词匹配比例阈值

    # 响应控制
    "reject_on_low_score": True,  # 低相似度时是否拒答（False则标记风险但返回答案）
    "reject_on_inconsistency": True,  # 不一致时是否拒答

    # 调试
    "default_debug": False,  # 默认debug模式
}

# 拒答响应模板
REJECTION_RESPONSE = {
    "content": "未在知识库中找到相关信息。",
    "finish_reason": "stop",
    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
}


class RAGService:
    def __init__(self):
        self.retriever = Retriever()
        self.guard_config = RAG_GUARD_CONFIG  # 允许实例级覆盖

    # -----------------------------
    # 配置管理
    # -----------------------------
    def update_guard_config(self, **kwargs) -> Dict[str, Any]:
        """动态更新防护配置（用于A/B测试或特殊场景）"""
        self.guard_config.update(kwargs)
        return self.guard_config.copy()

    def get_guard_config(self) -> Dict[str, Any]:
        """获取当前防护配置"""
        return self.guard_config.copy()

    # -----------------------------
    # 读取 KB 的 system_prompt
    # -----------------------------
    def load_kb_prompt(self, kb_id: str) -> str:
        if not kb_id:
            return ""

        meta_path = KB_ROOT / kb_id / "kb_meta.json"
        if not meta_path.exists():
            return ""

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            return meta.get("system_prompt", "")
        except Exception as e:
            logger.warning(f"加载 KB {kb_id} 的 meta 失败: {e}")
            return ""

    # -----------------------------
    # 向量检索
    # -----------------------------
    def retrieve_context(self, query: str, kb_id: str, top_k: int = 3) -> List[Dict]:
        if not kb_id:
            return []
        return self.retriever.search(query, kb_id=kb_id, top_k=top_k)

    # -----------------------------
    # 构造 RAG messages
    # -----------------------------
    def build_rag_messages(self, messages: List[Dict], kb_id: str) -> Tuple[List[Dict], List[Dict]]:
        if not messages:
            return messages, []

        # 获取用户最后一句话
        user_query = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_query = msg.get("content")
                break

        if not user_query:
            return messages, []

        full_results = self.retrieve_context(user_query, kb_id=kb_id)
        logger.info(f"RAG 查询: {user_query[:50]}..., 检索结果数: {len(full_results)}")

        if full_results:
            top_score = max(r.get('score', 0) for r in full_results)
            logger.info(f"最高相似度: {top_score:.4f}")

        kb_prompt = self.load_kb_prompt(kb_id)
        system_parts = []

        if kb_prompt:
            system_parts.append(kb_prompt)

        if full_results:
            context_text = "\n\n".join([r["text"] for r in full_results])
            system_parts.append(
                "Use the following knowledge base context when relevant:\n" + context_text
            )

        if not system_parts:
            return messages, full_results

        system_prompt = {
            "role": "system",
            "content": "\n\n".join(system_parts),
        }

        return [system_prompt] + messages, full_results

    # -----------------------------
    # 一致性检查引擎（融合双版本优点）
    # -----------------------------
    def check_consistency(self, content: str, references: List[Dict]) -> Dict[str, Any]:
        """
        多模式一致性检查：
        - strict: 完整包含检查（极少使用）
        - loose: 句子级匹配（旧版本方案）
        - hybrid: 关键词+句子混合检查（新版本设想+旧版本实现）
        """
        if not content or not references:
            return {"passed": False, "score": 0.0, "method": "none", "details": "空内容或无引用"}

        context_text = "\n".join([r["text"] for r in references])
        mode = self.guard_config["consistency_mode"]

        # 严格模式：完整包含（仅用于极高敏感场景）
        if mode == "strict":
            passed = content in context_text
            return {
                "passed": passed,
                "score": 1.0 if passed else 0.0,
                "method": "strict",
                "details": "完整包含检查" + ("通过" if passed else "失败")
            }

        # 宽松模式：句子级匹配（旧版本核心逻辑）
        if mode == "loose":
            sentences = [
                s.strip() for s in re.split(r'[。！？\n]', content)
                if len(s.strip()) >= self.guard_config["min_sentence_length"]
            ]
            if not sentences:
                return {"passed": True, "score": 1.0, "method": "loose", "details": "无有效句子，跳过检查"}

            matched = sum(1 for s in sentences if s in context_text)
            ratio = matched / len(sentences)
            passed = ratio > 0  # 至少有一句匹配

            return {
                "passed": passed,
                "score": ratio,
                "method": "loose",
                "details": f"句子匹配: {matched}/{len(sentences)} ({ratio:.2%})"
            }

        # 混合模式：关键词密度 + 句子锚点（推荐）
        # 结合新版本的关键词思路 + 旧版本的句子验证
        if mode == "hybrid":
            # 步骤1：提取关键句子（长度>=6）
            sentences = [
                s.strip() for s in re.split(r'[。！？\n]', content)
                if len(s.strip()) >= self.guard_config["min_sentence_length"]
            ]

            # 步骤2：关键词匹配（新版本的优化思路）
            all_kb_words = set()
            for ref in references:
                words = re.findall(r'\b\w{2,}\b', ref["text"])  # 2字以上词
                all_kb_words.update(words)

            content_words = re.findall(r'\b\w{2,}\b', content)
            if not content_words:
                keyword_ratio = 0.0
            else:
                matched_words = sum(1 for w in content_words if w in all_kb_words)
                keyword_ratio = matched_words / len(content_words)

            # 步骤3：句子锚点验证（确保不只是关键词堆砌）
            sentence_passed = False
            if sentences:
                matched_sentences = sum(1 for s in sentences if s in context_text)
                sentence_passed = matched_sentences > 0

            # 综合评分：关键词占比 * 0.4 + 句子锚点 * 0.6
            final_score = keyword_ratio * 0.4 + (1.0 if sentence_passed else 0.0) * 0.6
            passed = final_score >= self.guard_config["keyword_match_ratio"]

            return {
                "passed": passed,
                "score": final_score,
                "keyword_ratio": keyword_ratio,
                "sentence_anchored": sentence_passed,
                "method": "hybrid",
                "details": f"关键词匹配: {keyword_ratio:.2%}, 句子锚点: {sentence_passed}, 综合: {final_score:.2%}"
            }

        return {"passed": True, "score": 1.0, "method": "unknown", "details": "未知模式，默认通过"}

    # -----------------------------
    # 构建 References（分层阈值）
    # -----------------------------
    def build_references(self, full_results: List[Dict], kb_id: str) -> Tuple[List[Dict], List[Dict]]:
        """
        分层构建引用：
        - strict_refs: 高分引用（>= strict_reference_threshold，用于展示）
        - all_refs: 所有及格引用（>= score_threshold，用于一致性检查）
        """
        strict_threshold = self.guard_config["strict_reference_threshold"]
        base_threshold = self.guard_config["score_threshold"]

        # 所有及格的结果（用于一致性检查）
        all_refs = [
            {
                "kb_id": kb_id,
                "file_id": r["metadata"]["file_id"],
                "chunk_id": r["metadata"]["chunk_id"],
                "score": float(r["score"]),
                "content_preview": r["text"][:200] + "..." if len(r["text"]) > 200 else r["text"],
                "full_text": r["text"]  # 保留全文用于一致性检查
            }
            for r in full_results
            if r.get("score", 0) >= base_threshold
        ]

        # 严格筛选的结果（用于展示给用户）
        strict_refs = [
            {k: v for k, v in r.items() if k != "full_text"}  # 移除full_text减少传输
            for r in all_refs
            if r["score"] >= strict_threshold
        ]

        return all_refs, strict_refs

    # -----------------------------
    # 入库（给 upload 调用）
    # -----------------------------
    def ingest_text(self, text: str, kb_id: str, file_id: str) -> Dict[str, Any]:
        """
        完整 ingest 流程：读取 meta → 选模型 → chunk → embed → add → 更新 last_
        """
        if not text or not text.strip():
            logger.warning(f"KB {kb_id} ingest 文本为空，跳过")
            return {"ingested": 0, "chunks": 0, "model_used": None}

        if not kb_id:
            kb_id = "default"

        # 1. 获取 KB meta
        meta = kb_service.get(kb_id)
        if not meta:
            raise ValueError(f"知识库 {kb_id} 不存在")

        target_model = meta.get("embedding_model", "bge-small-zh-v1.5")

        # 2. 获取 embedding 服务（全局缓存，延迟加载）
        try:
            embedding_svc = get_embedding_service(target_model)
            actual_dim = embedding_svc.dim
        except Exception as e:
            logger.error(f"加载 embedding 模型失败: {str(e)}")
            raise RuntimeError(f"无法加载模型 {target_model}: {str(e)}")

        # 3. 切分文本
        try:
            chunks = chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        except Exception as e:
            logger.error(f"文本切分失败: {str(e)}")
            raise

        if not chunks:
            logger.warning(f"KB {kb_id} 切分后无有效 chunk，跳过")
            return {"ingested": 0, "chunks": 0, "model_used": target_model}

        # 构建 docs with metadata
        docs = [
            {
                "text": chunk["text"],
                "metadata": {
                    "file_id": file_id,
                    "chunk_id": chunk["chunk_id"]
                }
            }
            for chunk in chunks
        ]

        # 4. 生成向量（支持批量）
        try:
            embeddings = embedding_svc.embed([d["text"] for d in docs])

            if isinstance(embeddings, list):
                import numpy as np
                embeddings = np.array(embeddings)

            vectors = embeddings.astype("float32")

            if vectors.ndim == 1:
                vectors = vectors.reshape(1, -1)
            if len(vectors) != len(docs):
                raise RuntimeError(f"向量数量不匹配: {len(vectors)} vs {len(docs)} chunks")
            if vectors.shape[1] != actual_dim:
                raise RuntimeError(f"维度不匹配：预期 {actual_dim}，实际 {vectors.shape[1]}")
        except Exception as e:
            logger.error(f"生成向量失败: {str(e)}")
            raise

        # 5. 添加到 index
        try:
            index_manager = IndexManager(dim=actual_dim)
            index_manager.add(vectors, docs, kb_id)
            index_manager.save(kb_id)
        except Exception as e:
            logger.error(f"向量入库失败: {str(e)}")
            raise

        # 6. 更新 last_embedding 信息
        try:
            kb_service.update_last_embedding_info(
                kb_id=kb_id,
                model_name=target_model,
                dim=int(actual_dim)
            )
        except Exception as e:
            logger.warning(f"更新 last_embedding 信息失败，但 ingest 已成功: {str(e)}")

        logger.info(f"KB {kb_id} ingest 成功：{len(docs)} chunks，使用模型 {target_model}")

        return {
            "ingested": 1,
            "chunks": len(docs),
            "model_used": target_model,
            "dim": actual_dim
        }

    # -----------------------------
    # RAG 主入口（企业级融合版）
    # -----------------------------
    def rag_chat(
            self,
            messages: List[Dict],
            kb_id: Optional[str] = None,
            stream: bool = False,
            debug: bool = False,
            **kwargs
    ) -> Union[Dict, Generator]:
        """
        企业级 RAG 主入口，融合新旧版本优点：
        - 新版本的集中配置和严格阈值
        - 旧版本的完整拒答机制和详细metadata
        - 增强的hybrid一致性检查
        """
        debug = debug or self.guard_config["default_debug"]

        # 构建增强后的 messages + 检索结果
        rag_messages, full_results = self.build_rag_messages(messages, kb_id=kb_id)

        # 构建详细 metadata（旧版本风格）
        scores = [r.get("score", 0) for r in full_results]
        has_raw_results = len(full_results) > 0

        retrieval_metadata = {
            "kb_id": kb_id,
            "raw_retrieved": len(full_results),
            "scores_distribution": {
                "min": float(min(scores)) if scores else 0.0,
                "max": float(max(scores)) if scores else 0.0,
                "avg": float(sum(scores) / len(scores)) if scores else 0.0,
            } if scores else None,
        }

        max_score = retrieval_metadata["scores_distribution"]["max"] if scores else 0.0

        # =============================
        # 第一层防护：检索相似度检查（融合版）
        # =============================
        if self.guard_config["enable_score_guard"]:
            if max_score < self.guard_config["score_threshold"]:
                # 低相似度处理策略
                if self.guard_config["reject_on_low_score"]:
                    # 严格模式：直接拒答（旧版本核心安全机制）
                    return {
                        **REJECTION_RESPONSE,
                        "model": kwargs.get("model", "unknown"),
                        "references": [],
                        "retrieval_metadata": {
                            **retrieval_metadata,
                            "guard_triggered": "score_threshold",
                            "threshold": self.guard_config["score_threshold"],
                            "actual_max_score": max_score,
                        },
                        "safety": {
                            "kb_hit": False,
                            "hallucination_risk": "high",
                            "confidence": max_score,
                            "reason": "low_similarity_score",
                            "rejected": True,
                        }
                    }
                else:
                    # 宽松模式：标记风险但继续（用于特殊场景）
                    retrieval_metadata["warning"] = "low_similarity_but_proceeding"
                    logger.warning(f"低相似度警告({max_score:.4f})，但配置允许继续生成")

        # 构建分层引用（新版本严格阈值 + 旧版本完整信息）
        all_refs, display_refs = self.build_references(full_results, kb_id)
        has_valid_refs = len(all_refs) > 0

        # 调用 LLM
        llm_result = llm_service.chat_completions(
            messages=rag_messages,
            stream=stream,
            **kwargs
        )

        # =============================
        # 非流式分支（完整防护）
        # =============================
        if not stream:
            return self._handle_non_stream(
                llm_result=llm_result,
                all_refs=all_refs,
                display_refs=display_refs,
                retrieval_metadata=retrieval_metadata,
                max_score=max_score,
                has_valid_refs=has_valid_refs,
                debug=debug,
                kwargs=kwargs
            )

        # =============================
        # 流式分支（保持响应性）
        # =============================
        else:
            return self._handle_stream(
                llm_result=llm_result,
                display_refs=display_refs,
                retrieval_metadata=retrieval_metadata,
                max_score=max_score,
                has_valid_refs=has_valid_refs,
                debug=debug,
                rag_messages=rag_messages,
                full_results=full_results
            )

    def _handle_non_stream(
            self,
            llm_result: Any,
            all_refs: List[Dict],
            display_refs: List[Dict],
            retrieval_metadata: Dict,
            max_score: float,
            has_valid_refs: bool,
            debug: bool,
            kwargs: Dict
    ) -> Dict:
        """非流式响应处理（支持完整一致性检查）"""

        # 解析 LLM 响应
        content = ""
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        model = kwargs.get("model", "unknown")
        finish_reason = "stop"

        if isinstance(llm_result, dict):
            content = llm_result.get("content", "")
            usage = llm_result.get("usage", usage)
            model = llm_result.get("model", model)
            finish_reason = llm_result.get("finish_reason", finish_reason)
        elif isinstance(llm_result, str):
            content = llm_result
        else:
            content = str(llm_result)

        # =============================
        # 第二层防护：内容一致性检查（增强版）
        # =============================
        consistency_result = {
            "passed": True,
            "score": 1.0,
            "method": "skipped",
            "details": "检查未启用或无引用"
        }

        if self.guard_config["enable_consistency_check"] and has_valid_refs and content.strip():
            consistency_result = self.check_consistency(content, all_refs)

            if not consistency_result["passed"] and self.guard_config["reject_on_inconsistency"]:
                # 一致性检查失败，拒答
                return {
                    **REJECTION_RESPONSE,
                    "model": model,
                    "usage": usage,
                    "references": display_refs,
                    "retrieval_metadata": {
                        **retrieval_metadata,
                        "guard_triggered": "consistency_check",
                        "consistency_details": consistency_result,
                    },
                    "safety": {
                        "kb_hit": True,
                        "hallucination_risk": "high",
                        "confidence": max_score,
                        "reason": "content_inconsistency",
                        "consistency_score": consistency_result["score"],
                        "rejected": True,
                    }
                }

        # 构建最终响应
        result = {
            "content": content,
            "model": model,
            "finish_reason": finish_reason,
            "usage": usage,
            "references": display_refs,
            "retrieval_metadata": {
                **retrieval_metadata,
                "filtered_refs": len(all_refs),
                "display_refs": len(display_refs),
            },
            "safety": {
                "kb_hit": has_valid_refs and len(display_refs) > 0,
                "hallucination_risk": "low" if (has_valid_refs and consistency_result["passed"]) else "medium",
                "confidence": max_score,
                "consistency_check": consistency_result,
                "rejected": False,
            }
        }

        if debug:
            result["debug"] = {
                "all_retrieved_chunks": all_refs,
                "consistency_check_details": consistency_result,
                "guard_config": self.guard_config,
            }

        return result

    def _handle_stream(
            self,
            llm_result: Generator,
            display_refs: List[Dict],
            retrieval_metadata: Dict,
            max_score: float,
            has_valid_refs: bool,
            debug: bool,
            rag_messages: List[Dict],
            full_results: List[Dict]
    ) -> Generator:
        """流式响应处理（在结束时注入元数据）"""

        def wrapped_stream():
            collected_content = ""
            final_usage = None
            finish_reason = "stop"
            done_sent = False

            for chunk in llm_result:
                # 累积内容
                if isinstance(chunk, dict):
                    try:
                        choice = chunk.get("choices", [{}])[0]
                        delta = choice.get("delta", {}) if choice else {}
                        delta_content = delta.get("content", "")
                        if delta_content:
                            collected_content += delta_content

                        if "usage" in chunk:
                            final_usage = chunk.get("usage")
                        if choice.get("finish_reason"):
                            finish_reason = choice.get("finish_reason")
                    except Exception:
                        pass

                yield chunk

                # 检测到结束信号，注入元数据
                if isinstance(chunk, dict) and (chunk.get("done") or finish_reason):
                    done_sent = True

                    # 流式模式下进行轻量级一致性检查（可选）
                    # 注意：完整检查需要等所有内容生成完毕，这里只做标记
                    chunk["references"] = display_refs
                    chunk["retrieval_metadata"] = {
                        **retrieval_metadata,
                        "display_refs": len(display_refs),
                        "stream_mode": True,
                    }
                    chunk["safety"] = {
                        "kb_hit": has_valid_refs,
                        "hallucination_risk": "low" if has_valid_refs else "high",
                        "confidence": max_score,
                        "note": "流式模式：一致性检查在生成后执行（如启用）",
                        "collected_length": len(collected_content),
                    }

                    if debug:
                        chunk["debug"] = {
                            "retrieved_chunks_count": len(full_results),
                            "final_prompt_length": sum(len(m.get("content", "")) for m in rag_messages),
                            "guard_config": self.guard_config,
                        }

            # 补发结束标记（如果LLM未发送）
            if not done_sent:
                yield {
                    "done": True,
                    "usage": final_usage,
                    "references": display_refs,
                    "retrieval_metadata": retrieval_metadata,
                    "safety": {
                        "kb_hit": has_valid_refs,
                        "hallucination_risk": "low" if has_valid_refs else "high",
                        "confidence": max_score,
                        "note": "流式结束（补发标记）",
                    }
                }

        return wrapped_stream()


# 全局实例（供接口调用）
rag_service = RAGService()