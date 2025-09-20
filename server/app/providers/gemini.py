from __future__ import annotations
import os
import json
import asyncio
from typing import AsyncIterator, List, Dict, Any
import httpx

from app.schemas.chat import ChatRequest, ModelInfo
from app.config import get_settings


class GeminiProvider:
    id = "gemini"

    async def list_models(self) -> List[ModelInfo]:
        # Minimal set for MVP — use widely available model IDs
        return [
            ModelInfo(id="gemini-1.5-flash", name="Gemini 2.5 Flash", context_length=1_000_000),
        ]

    def _to_gemini_payload(self, request: ChatRequest) -> Dict[str, Any]:
        # Convert ChatRequest.messages into Gemini "contents"
        # Skip any messages with empty content (client may include a placeholder assistant message)
        contents: List[Dict[str, Any]] = []
        for m in request.messages:
            text = (m.content or "").strip()
            if not text:
                continue
            # Gemini roles: "user" and "model". Map OpenAI roles accordingly.
            if m.role == "assistant":
                role = "model"
            else:
                # Map both user and system to user
                role = "user"
            contents.append({
                "role": role,
                "parts": [{"text": text}]
            })
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature or 0.7,
                # Gemini uses maxOutputTokens rather than max_tokens
                "maxOutputTokens": request.maxTokens or 512,
            },
        }
        return payload

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        settings = get_settings()
        api_key = (
            getattr(settings, "google_api_key", None)
            or getattr(settings, "gemini_api_key", None)
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("GEMINI_API_KEY")
        )
        if not api_key:
            # Fallback mock stream
            async for chunk in self._mock_stream(request):
                yield chunk
            return

        # Gemini non-streaming endpoint (more reliable across clients)
        base = "https://generativelanguage.googleapis.com/v1beta"
        url = f"{base}/models/{request.model}:generateContent?key={api_key}"
        payload = self._to_gemini_payload(request)

        # Retry loop for transient errors; we will make a normal POST and then
        # emit SSE-compatible chunks to the client.
        max_attempts = 3
        backoff = 0.8
        for attempt in range(1, max_attempts + 1):
            try:
                timeout = httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=10.0)
                async with httpx.AsyncClient(timeout=timeout, trust_env=True) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    obj = resp.json()
                    candidates = obj.get("candidates") or []
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for p in parts:
                            text = p.get("text")
                            if text:
                                # Emit as SSE-compatible chunk
                                yield "data: " + json.dumps({"content": text}) + "\n\n"
                    # Signal done either way
                    yield "data: {\"done\": true}\n\n"
                    return
            except Exception as e:
                if attempt < max_attempts:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                yield "data: " + json.dumps({"content": f"[gemini] request failed: {str(e)}"}) + "\n\n"
                yield "data: {\"done\": true}\n\n"
                return

    async def _mock_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        text = f"[gemini-mock] You said: '{request.messages[-1].content}'"
        for i, word in enumerate(text.split()):
            yield "data: " + json.dumps({"content": word + (" " if i < len(text.split()) - 1 else "")}) + "\n\n"
            await asyncio.sleep(0.05)
        yield "data: {\"done\": true}\n\n"
