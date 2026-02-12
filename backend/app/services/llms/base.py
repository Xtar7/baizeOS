from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Generator, Union


class BaseLLM(ABC):
    """
    所有 LLM 后端的抽象基类
    """

    def __init__(self, model_path: Path):
        self.model_path = model_path
        self.model_name = model_path.stem
        self.capabilities = self.detect_capabilities()

    @abstractmethod
    def load(self):
        """加载模型"""
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[Dict],
        system_prompt: str,
        stream: bool = False
    ) -> Union[str, Generator[str, None, None]]:
        """对话接口"""
        pass

    def detect_capabilities(self) -> dict:
        name = self.model_name.lower()

        return {
            "chat": True,
            "code": "coder" in name or "code" in name,
            "vision": "vision" in name or "vl" in name,
            "embedding": "embed" in name,
        }
