from __future__ import annotations
import os
import json
import asyncio
from typing import AsyncIterator, List
import httpx

from app.schemas.chat import ChatRequest, ModelInfo
from app.config import get_settings


class DeepSeekProvider:
    id = "deepseek"

    async def list_models(self) -> List[ModelInfo]:
        # Common public DeepSeek models (adjust as needed)
        return [
            ModelInfo(id="deepseek-chat", name="DeepSeek Chat", context_length=128_000),
            ModelInfo(id="deepseek-reasoner", name="DeepSeek Reasoner", context_length=128_000),
        ]

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        settings = get_settings()
        api_key = os.getenv("DEEPSEEK_API_KEY") or getattr(settings, "deepseek_api_key", None)
        if not api_key:
            async for chunk in self._mock_stream(request):
                yield chunk
            return

        # DeepSeek exposes an OpenAI-compatible endpoint
        payload = {
            "model": request.model,
            "messages": [m.dict() for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.maxTokens or getattr(request, "max_tokens", 512),
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        url = "https://api.deepseek.com/v1/chat/completions"

        max_attempts = 3
        backoff = 0.8
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                timeout = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)
                async with httpx.AsyncClient(timeout=timeout, trust_env=True) as client:
                    async with client.stream("POST", url, headers=headers, json=payload) as resp:
                        resp.raise_for_status()
                        async for line in resp.aiter_lines():
                            if not line:
                                continue
                            if line.startswith("data: "):
                                data = line[len("data: "):]
                                if data.strip() == "[DONE]":
                                    yield "data: {\"done\": true}\n\n"
                                    break
                                try:
                                    obj = json.loads(data)
                                    delta = obj.get("choices", [{}])[0].get("delta", {})
                                    content = delta.get("content")
                                    if content:
                                        yield "data: " + json.dumps({"content": content}) + "\n\n"
                                except Exception:
                                    continue
                        return
            except Exception as e:
                last_error = e
                if attempt < max_attempts:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                # Friendly message mapping
                friendly = None
                status = None
                body = None
                try:
                    if hasattr(e, "response") and e.response is not None:
                        status = e.response.status_code
                        body = await e.response.aread()
                        body = body.decode("utf-8", errors="ignore")
                except Exception:
                    pass
                if status == 402:
                    friendly = "[DeepSeek] Payment required. Please enable billing on your DeepSeek account or use a model available to your plan."
                elif status == 429:
                    friendly = "[DeepSeek] Too many requests. You have hit the rate limit. Please wait a moment and try again."
                detail = friendly or f"[deepseek] request failed after {max_attempts} attempts: {str(e)}"
                if body and not friendly:
                    detail += f"\nProvider response: {body}"
                yield "data: " + json.dumps({"content": detail}) + "\n\n"
                yield "data: {\"done\": true}\n\n"
                return

    async def _mock_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        text = f"[deepseek-mock] You said: '{request.messages[-1].content}'"
        for i, tok in enumerate(text.split()):
            yield "data: " + json.dumps({"content": tok + (" " if i < len(text.split()) - 1 else "")}) + "\n\n"
            await asyncio.sleep(0.05)
        yield "data: {\"done\": true}\n\n"
