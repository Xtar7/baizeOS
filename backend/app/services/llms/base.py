# app/services/llms/base.py
from abc import ABC, abstractmethod
from pathlib import Path


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
    def chat(self, message: str) -> str:
        """对话接口"""
        pass

    def detect_capabilities(self) -> dict:
        """
        根据模型名简单判断能力
        后续可以改成读取 capability.yaml
        """
        name = self.model_name.lower()

        return {
            "chat": True,
            "code": "coder" in name or "code" in name,
            "vision": "vision" in name or "vl" in name,
            "embedding": "embed" in name,
        }
