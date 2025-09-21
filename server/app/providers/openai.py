from __future__ import annotations
import os
import json
import asyncio
from typing import AsyncIterator, List
import httpx

from app.schemas.chat import ChatRequest, ModelInfo
from app.config import get_settings


class OpenAIProvider:
    id = "openai"

    async def list_models(self) -> List[ModelInfo]:
        # Static list for MVP
        return [
            ModelInfo(id="gpt-4o-mini", name="GPT-4o Mini", context_length=128_000),
            ModelInfo(id="gpt-4o", name="GPT-4o", context_length=128_000),
            ModelInfo(id="gpt-3.5-turbo", name="GPT-3.5 Turbo", context_length=16_385),
        ]

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        settings = get_settings()
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Graceful fallback: mock stream
            async for chunk in self._mock_stream(request):
                yield chunk
            return

        payload = {
            "model": request.model,
            "messages": [m.dict() for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.maxTokens or request.max_tokens if hasattr(request, "max_tokens") else 512,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Retry with exponential backoff for transient network issues
        max_attempts = 3
        backoff = 0.8
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                timeout = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)
                async with httpx.AsyncClient(timeout=timeout, trust_env=True) as client:
                    async with client.stream(
                        "POST",
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    ) as resp:
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
                                        chunk = json.dumps({"content": content})
                                        yield "data: " + chunk + "\n\n"
                                except Exception:
                                    # if parsing fails, ignore this line
                                    continue
                        return
            except Exception as e:
                last_error = e
                if attempt < max_attempts:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                # Friendly error mapping
                friendly = None
                status = None
                provider_body = None
                try:
                    if hasattr(e, "response") and e.response is not None:
                        status = e.response.status_code
                        body = await e.response.aread()
                        provider_body = body.decode("utf-8", errors="ignore")
                except Exception:
                    pass
                if status == 429:
                    friendly = "[OpenAI] Too many requests. You have hit the rate limit. Please wait a moment and try again."
                elif status in (401, 403):
                    friendly = "[OpenAI] Authentication/permission issue. Check your API key and model access."
                elif status == 400:
                    friendly = "[OpenAI] Bad request. Please verify the model id and payload parameters."
                message = friendly or f"[openai] request failed after {max_attempts} attempts: {str(e)}"
                if provider_body and not friendly:
                    message += f"\nProvider response: {provider_body}"
                yield "data: " + json.dumps({"content": message}) + "\n\n"
                yield "data: {\"done\": true}\n\n"
                return

    async def _mock_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        text = f"[openai-mock] You said: '{request.messages[-1].content}'"
        words = text.split()
        for i, word in enumerate(words):
            content = word + (" " if i < len(words) - 1 else "")
            chunk = json.dumps({"content": content})
            yield "data: " + chunk + "\n\n"
            await asyncio.sleep(0.05)
        yield "data: {\"done\": true}\n\n"
