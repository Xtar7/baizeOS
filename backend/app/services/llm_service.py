from pathlib import Path
from app.config.settings import (
    LLM_SCAN_PATH,
    DEFAULT_CHAT_MODEL,
    PROMPT_DIR,
    DEFAULT_PROMPT_NAME
)
from app.services.llms.llama_cpp import LlamaCppLLM


class LLMService:
    def __init__(self):
        self.models = []          # 所有模型路径
        self.model_map = {}       # name -> path
        self.active_llm = None    # 当前默认模型实例
        self.active_model_name = None

        self.scan_models()
        self.select_model()

    # ----------------------------
    # 1. 模型扫描
    # ----------------------------
    def scan_models(self):
        if not LLM_SCAN_PATH.exists():
            raise RuntimeError(f"模型目录不存在: {LLM_SCAN_PATH}")

        print(f"[LLM] 扫描模型目录: {LLM_SCAN_PATH}")

        for file in LLM_SCAN_PATH.iterdir():
            if file.suffix.lower() == ".gguf":
                model_name = file.stem
                print(f"[LLM] 发现模型: {model_name}")

                self.models.append(file)
                self.model_map[model_name] = file

        if not self.models:
            raise RuntimeError("未发现任何 GGUF 模型")

    # ----------------------------
    # 2. 自动选择默认模型
    # ----------------------------
    def select_model(self):
        model_path = None

        # 优先使用配置指定模型
        if DEFAULT_CHAT_MODEL:
            for name, path in self.model_map.items():
                if DEFAULT_CHAT_MODEL in name:
                    model_path = path
                    self.active_model_name = name
                    break

        # 否则选择第一个
        if not model_path:
            model_path = self.models[0]
            self.active_model_name = model_path.stem

        print(f"[LLM] 选择默认模型: {self.active_model_name}")

        self.active_llm = LlamaCppLLM(model_path)

        print("[LLM] 模型能力:", self.active_llm.capabilities)

    # ----------------------------
    # 3. 根据请求选择模型
    # ----------------------------
    def get_llm(self, model_name: str | None):
        """
        根据请求的 model 参数选择模型
        """
        if not model_name:
            return self.active_llm

        # 模糊匹配
        for name, path in self.model_map.items():
            if model_name in name:
                print(f"[LLM] 临时切换模型: {name}")
                return LlamaCppLLM(path)

        raise ValueError(f"未找到模型: {model_name}")

    # ----------------------------
    # 4. 加载默认 prompt
    # ----------------------------
    def load_prompt(self, prompt_name: str):
        prompt_file = PROMPT_DIR / f"{prompt_name}.txt"

        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt 不存在: {prompt_file}")

        return prompt_file.read_text(encoding="utf-8").strip()

    # ----------------------------
    # 5. 注入 system prompt
    # ----------------------------
    def inject_system_prompt(self, messages, prompt_name):
        """
        如果 messages 中没有 system，则注入默认 prompt
        """
        if not messages:
            messages = []

        has_system = any(m.get("role") == "system" for m in messages)

        if not has_system:
            system_prompt = self.load_prompt(prompt_name)
            messages = [
                {"role": "system", "content": system_prompt}
            ] + messages

        return messages

    # ----------------------------
    # 6. OpenAI 兼容接口
    # ----------------------------
    def completions(
        self,
        messages,
        stream=False,
        prompt_name=DEFAULT_PROMPT_NAME,
        model=None
    ):
        """
        OpenAI 风格对话入口
        """
        if not messages:
            raise ValueError("messages 不能为空")

        llm = self.get_llm(model)

        # 注入默认 system prompt
        messages = self.inject_system_prompt(messages, prompt_name)

        # 非流式
        if not stream:
            return llm.chat(messages)

        # 流式
        return llm.stream_chat(messages)


# 全局单例
llm_service = LLMService()