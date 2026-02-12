from pathlib import Path
from app.config.settings import LLM_SCAN_PATH, DEFAULT_CHAT_MODEL
from app.services.llms.llama_cpp import LlamaCppLLM

PROMPT_DIR = Path("E:/baizeOS/config/prompts")


def load_system_prompt(prompt_name: str) -> str:
    prompt_file = PROMPT_DIR / f"{prompt_name}.txt"

    if not prompt_file.exists():
        return "You are a helpful assistant."

    return prompt_file.read_text(encoding="utf-8").strip()


class LLMService:
    def __init__(self):
        self.models = []
        self.active_llm = None

        self.scan_models()
        self.select_model()

    # ----------------------------
    # 模型扫描
    # ----------------------------
    def scan_models(self):
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
    # 自动选择模型
    # ----------------------------
    def select_model(self):
        model_path = None

        if DEFAULT_CHAT_MODEL:
            for m in self.models:
                if DEFAULT_CHAT_MODEL in m.name:
                    model_path = m
                    break

        if not model_path:
            model_path = self.models[0]

        print(f"[LLM] 选择模型: {model_path.name}")

        self.active_llm = LlamaCppLLM(model_path)

        print("[LLM] 模型能力:", self.active_llm.capabilities)

    # ----------------------------
    # 对外接口
    # ----------------------------
    def chat(self, messages, stream=False, prompt_name="default"):
        if not self.active_llm:
            raise RuntimeError("LLM 未初始化")

        system_prompt = load_system_prompt(prompt_name)

        return self.active_llm.chat(
            messages=messages,
            system_prompt=system_prompt,
            stream=stream
        )


# 全局单例
llm_service = LLMService()