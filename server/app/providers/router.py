from __future__ import annotations
from typing import Dict, List

from app.providers.openai import OpenAIProvider
from app.providers.anthropic import AnthropicProvider
from app.providers.deepseek import DeepSeekProvider
from app.providers.gemini import GeminiProvider
from app.providers.openrouter import OpenRouterProvider
from app.schemas.chat import ModelInfo, ChatRequest


class ProviderRouter:
    def __init__(self) -> None:
        # Register enabled providers here
        self.providers = {
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "deepseek": DeepSeekProvider(),
            # OpenRouter as additional providers for listing and routing
            "openrouter": OpenRouterProvider(mode="any"),
            "openrouter_free": OpenRouterProvider(mode="free"),
            "openrouter_paid": OpenRouterProvider(mode="paid"),
        }
        # Map model prefixes or exact ids to providers
        self.model_provider_map: Dict[str, str] = {
            # simple mapping; extend as needed
            "gpt-": "openai",
            "claude-": "anthropic",
            "deepseek-": "deepseek",
            "gemini": "gemini",
            "gemini-": "gemini",
            "gemini-2.5": "gemini",
        }

    async def list_models(self) -> Dict[str, List[ModelInfo]]:
        result: Dict[str, List[ModelInfo]] = {}
        for pid, provider in self.providers.items():
            result[pid] = await provider.list_models()
        return result

    def resolve_provider_id(self, model: str) -> str:
        # If model id is namespaced like "provider/model", route via OpenRouter
        if "/" in model:
            return "openrouter"
        for prefix, pid in self.model_provider_map.items():
            if model.startswith(prefix):
                return pid
        # default to openai
        return "openai"

    def get_provider(self, model: str):
        pid = self.resolve_provider_id(model)
        return self.providers[pid]


router = ProviderRouter()
