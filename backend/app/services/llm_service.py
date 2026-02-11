# app/services/llm_service.py

from app.config.settings import LLM_SCAN_PATH, DEFAULT_CHAT_MODEL
from app.services.llms.llama_cpp import LlamaCppLLM


class LLMService:
    def __init__(self):
        self.models = []
        self.active_llm = None

        self.scan_models()
        self.select_model()

    # ----------------------------
    # 1. 模型扫描
    # ----------------------------
    def scan_models(self):
        # print("[DEBUG] LLM_SCAN_PATH 类型:", type(LLM_SCAN_PATH))
        # print("[DEBUG] LLM_SCAN_PATH 完整路径:", str(LLM_SCAN_PATH))
        # print("[DEBUG] 是否存在:", LLM_SCAN_PATH.exists())
        # print("[DEBUG] 是否是目录:", LLM_SCAN_PATH.is_dir())

        if not LLM_SCAN_PATH.exists():
            raise RuntimeError(f"模型目录不存在: {LLM_SCAN_PATH}")

        print(f"[LLM] 扫描模型目录: {LLM_SCAN_PATH}")

        for file in LLM_SCAN_PATH.iterdir():
            if file.suffix.lower() == ".gguf":
                print(f"[LLM] 发现模型: {file.name}")
                self.models.append(file)

        if not self.models:
            raise RuntimeError("未发现任何 GGUF 模型")

    # ----------------------------
    # 2. 自动选择模型
    # ----------------------------
    def select_model(self):
        model_path = None

        # 优先使用配置指定模型
        if DEFAULT_CHAT_MODEL:
            for m in self.models:
                if DEFAULT_CHAT_MODEL in m.name:
                    model_path = m
                    break

        # 否则选择第一个
        if not model_path:
            model_path = self.models[0]

        print(f"[LLM] 选择模型: {model_path.name}")

        self.active_llm = LlamaCppLLM(model_path)

        print("[LLM] 模型能力:", self.active_llm.capabilities)

    # ----------------------------
    # 3. 对外接口
    # ----------------------------
    def chat(self, message: str) -> str:
        if not self.active_llm:
            raise RuntimeError("LLM 未初始化")

        return self.active_llm.chat(message)


# 全局单例
llm_service = LLMService()