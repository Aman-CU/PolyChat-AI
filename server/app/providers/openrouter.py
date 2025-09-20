from __future__ import annotations
import os
import json
import asyncio
from typing import AsyncIterator, List, Dict, Any
import httpx

from app.schemas.chat import ChatRequest, ModelInfo
from app.config import get_settings


class OpenRouterProvider:
    """OpenRouter unified provider.

    mode:
      - 'any': stream only, no model list filtering
      - 'free': list only free ($0) models
      - 'paid': list only paid models
    """

    def __init__(self, mode: str = "any") -> None:
        self.mode = mode
        if mode == "free":
            self.id = "openrouter_free"
        elif mode == "paid":
            self.id = "openrouter_paid"
        else:
            self.id = "openrouter"

    async def list_models(self) -> List[ModelInfo]:
        # Only provide lists when in free/paid mode
        if self.mode not in ("free", "paid"):
            return []
        settings = get_settings()
        api_url = "https://openrouter.ai/api/v1/models"
        timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=True) as client:
                resp = await client.get(api_url)
                resp.raise_for_status()
                data = resp.json().get("data", [])
        except Exception:
            # If fetch fails, return an empty list to avoid UI break
            return []

        models: List[ModelInfo] = []
        for m in data:
            pricing = m.get("pricing") or {}
            prompt = pricing.get("prompt")
            completion = pricing.get("completion")
            is_free = (str(prompt) == "0" and str(completion) == "0")
            if self.mode == "free" and not is_free:
                continue
            if self.mode == "paid" and is_free:
                continue
            mid = m.get("id") or m.get("slug")
            name = m.get("name") or mid
            ctx = m.get("context_length") or m.get("top_provider", {}).get("context_length") or 128000
            if isinstance(ctx, str):
                try:
                    ctx = int(ctx)
                except Exception:
                    ctx = 128000
            models.append(ModelInfo(id=mid, name=name, context_length=ctx))
        # Optionally limit to top N for performance
        return models[:100]

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        settings = get_settings()
        api_key = (
            os.getenv("OPENROUTER_API_KEY")
            or getattr(settings, "openrouter_api_key", None)
        )
        if not api_key:
            # Graceful mock
            async for chunk in self._mock_stream(request):
                yield chunk
            return

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        # Optional attribution headers (if configured)
        ref = os.getenv("OPENROUTER_HTTP_REFERER") or getattr(settings, "openrouter_http_referer", None)
        title = os.getenv("OPENROUTER_APP_TITLE") or getattr(settings, "openrouter_app_title", None)
        if ref:
            headers["HTTP-Referer"] = ref
        if title:
            headers["X-Title"] = title

        # For ":free" alias SKUs, allow OpenRouter to fallback within the free pool.
        is_free_alias = isinstance(request.model, str) and ":free" in request.model
        payload: Dict[str, Any] = {
            "model": request.model,
            "provider": {"allow_fallbacks": bool(is_free_alias)},
            "messages": [m.dict() for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.maxTokens or getattr(request, "max_tokens", 512),
            "stream": True,
        }
        # Only enforce strict models[] for non-free selections
        if not is_free_alias:
            payload["models"] = [request.model]

        url = "https://openrouter.ai/api/v1/chat/completions"

        # Retry & backoff
        max_attempts = 3
        backoff = 0.8
        for attempt in range(1, max_attempts + 1):
            try:
                timeout = httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=10.0)
                async with httpx.AsyncClient(timeout=timeout, trust_env=True) as client:
                    emitted_any = False
                    async with client.stream("POST", url, headers=headers, json=payload) as resp:
                        resp.raise_for_status()
                        surfaced_model = False
                        async for line in resp.aiter_lines():
                            if not line:
                                continue
                            if line.startswith("data: "):
                                data = line[len("data: "):]
                                if data.strip() == "[DONE]":
                                    # If the stream ended without emitting content, try non-stream fallback
                                    if not emitted_any:
                                        try:
                                            non_stream_payload = dict(payload)
                                            non_stream_payload["stream"] = False
                                            r2 = await client.post(url, headers=headers, json=non_stream_payload)
                                            r2.raise_for_status()
                                            obj2 = r2.json()
                                            text2 = (
                                                obj2.get("choices", [{}])[0]
                                                .get("message", {})
                                                .get("content")
                                            )
                                            if text2:
                                                yield "data: " + json.dumps({"content": text2}) + "\n\n"
                                        except Exception:
                                            pass
                                    yield "data: {\"done\": true}\n\n"
                                    break
                                # OpenRouter streams OpenAI-like chunks; forward as-is if possible
                                try:
                                    obj = json.loads(data)
                                    # Surface actual model used once if available
                                    if not surfaced_model and isinstance(obj, dict):
                                        used = obj.get("model")
                                        if used:
                                            surfaced_model = True
                                            yield "data: " + json.dumps({"content": f"[model: {used}]\n"}) + "\n\n"
                                    # Normalize to our client format: extract delta content
                                    content = None
                                    if obj.get("choices"):
                                        ch0 = obj["choices"][0]
                                        # Prefer streaming delta
                                        content = (ch0.get("delta") or {}).get("content")
                                        # Some providers send message.content even in stream
                                        if not content:
                                            content = (ch0.get("message") or {}).get("content")
                                    if content:
                                        emitted_any = True
                                        yield "data: " + json.dumps({"content": content}) + "\n\n"
                                except Exception:
                                    continue
                        return
            except Exception as e:
                if attempt < max_attempts:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                # Friendly error mapping
                status = None
                body_text = None
                try:
                    if hasattr(e, "response") and e.response is not None:
                        status = e.response.status_code
                        body = await e.response.aread()
                        body_text = body.decode("utf-8", errors="ignore")
                except Exception:
                    pass
                if status == 402:
                    msg = "[OpenRouter] Payment required. Add credits or choose a free model."
                elif status == 429:
                    msg = "[OpenRouter] Too many requests. Please slow down and try again shortly."
                elif status in (401, 403):
                    msg = "[OpenRouter] Authentication/permission issue. Check your API key and model access."
                elif status == 400:
                    msg = "[OpenRouter] Bad request. Verify model id and parameters."
                else:
                    msg = f"[openrouter] request failed after {max_attempts} attempts: {str(e)}"
                    if body_text:
                        msg += f"\nProvider response: {body_text}"
                yield "data: " + json.dumps({"content": msg}) + "\n\n"
                yield "data: {\"done\": true}\n\n"
                return

    async def _mock_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        text = f"[openrouter-mock] You said: '{request.messages[-1].content}'"
        for i, word in enumerate(text.split()):
            yield "data: " + json.dumps({"content": word + (" " if i < len(text.split()) - 1 else "")}) + "\n\n"
            await asyncio.sleep(0.05)
        yield "data: {\"done\": true}\n\n"
