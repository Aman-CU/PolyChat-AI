from __future__ import annotations
import os
import json
import asyncio
from typing import AsyncIterator, List
import httpx

from app.schemas.chat import ChatRequest, ModelInfo
from app.config import get_settings


class AnthropicProvider:
    id = "anthropic"

    async def list_models(self) -> List[ModelInfo]:
        # Common Claude models; adjust for your account/region.
        return [
            ModelInfo(id="claude-3-5-sonnet-latest", name="Claude 3.5 Sonnet", context_length=200_000),
            ModelInfo(id="claude-3-opus-latest", name="Claude 3 Opus", context_length=200_000),
        ]

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        settings = get_settings()
        api_key = os.getenv("ANTHROPIC_API_KEY") or getattr(settings, "anthropic_api_key", None)
        if not api_key:
            async for chunk in self._mock_stream(request):
                yield chunk
            return

        # Transform OpenAI-style messages to Anthropic format
        messages = []
        system_text_parts: list[str] = []
        for m in request.messages:
            text = (m.content or "").strip()
            if not text:
                continue
            if m.role == "system":
                system_text_parts.append(text)
                continue
            role = "assistant" if m.role == "assistant" else "user"
            messages.append({
                "role": role,
                "content": [{"type": "text", "text": text}],
            })

        payload = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.maxTokens or getattr(request, "max_tokens", 512),
            "temperature": request.temperature,
            "stream": True,
        }
        if system_text_parts:
            payload["system"] = "\n\n".join(system_text_parts)

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "accept": "text/event-stream",
        }

        url = "https://api.anthropic.com/v1/messages"

        max_attempts = 3
        backoff = 0.8
        for attempt in range(1, max_attempts + 1):
            try:
                timeout = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)
                async with httpx.AsyncClient(timeout=timeout, trust_env=True) as client:
                    async with client.stream("POST", url, headers=headers, json=payload) as resp:
                        resp.raise_for_status()
                        async for line in resp.aiter_lines():
                            if not line:
                                continue
                            # Anthropic returns event stream with "data: { ... }" too
                            if line.startswith("data: "):
                                data = line[len("data: "):]
                                if data.strip() == "[DONE]":
                                    yield "data: {\"done\": true}\n\n"
                                    break
                                try:
                                    obj = json.loads(data)
                                    etype = obj.get("type")
                                    # message_start, message_delta, content_block_start, content_block_delta {type:text_delta,text}
                                    if etype == "content_block_delta":
                                        delta = obj.get("delta", {})
                                        if delta.get("type") == "text_delta":
                                            content = delta.get("text")
                                            if content:
                                                yield "data: " + json.dumps({"content": content}) + "\n\n"
                                    elif etype == "message_delta":
                                        # Some versions send aggregated deltas here
                                        for d in obj.get("delta", {}).get("content", []) or []:
                                            if d.get("type") == "text_delta":
                                                t = d.get("text")
                                                if t:
                                                    yield "data: " + json.dumps({"content": t}) + "\n\n"
                                    elif etype == "message_stop":
                                        yield "data: {\"done\": true}\n\n"
                                        break
                                except Exception:
                                    continue
                        return
            except Exception as e:
                if attempt < max_attempts:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                # Friendly mapping
                friendly = None
                status = None
                detail = str(e)
                try:
                    if hasattr(e, "response") and e.response is not None:
                        status = e.response.status_code
                        body = await e.response.aread()
                        body_text = body.decode("utf-8", errors="ignore")
                        detail = body_text or detail
                except Exception:
                    pass
                if status == 429:
                    friendly = "[Anthropic] Too many requests. You have hit the rate limit. Please wait a moment and try again."
                elif status in (401, 403):
                    friendly = "[Anthropic] Authentication/permission issue. Please check your API key and ensure your account has access to this model."
                elif status == 400:
                    friendly = "[Anthropic] Bad request. The selected model may not be enabled for your account or the payload is invalid. Try a different Claude model (e.g., claude-3-5-sonnet-latest)."
                msg = friendly or f"[anthropic] request failed after {max_attempts} attempts: {detail}"
                err_msg = {"content": msg}
                yield "data: " + json.dumps(err_msg) + "\n\n"
                yield "data: {\"done\": true}\n\n"
                return

    async def _mock_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        text = f"[anthropic-mock] You said: '{request.messages[-1].content}'"
        for i, tok in enumerate(text.split()):
            yield "data: " + json.dumps({"content": tok + (" " if i < len(text.split()) - 1 else "")}) + "\n\n"
            await asyncio.sleep(0.05)
        yield "data: {\"done\": true}\n\n"
