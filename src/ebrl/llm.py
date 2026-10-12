"""Local-only LLM adapter. Cloud inference is rejected and there is no fallback."""
from __future__ import annotations

import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen

CLOUD_MARKERS = (
    "openai",
    "anthropic",
    "googleapis",
    "generativelanguage",
    "azure",
    "cohere",
    "mistral.ai",
    "groq.com",
    "together.ai",
    "openrouter",
)


class LocalOnlyViolation(RuntimeError):
    pass


class LocalLLMUnavailable(RuntimeError):
    pass


def assert_local_endpoint(base_url: str, allow_private_lan: bool = False) -> None:
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    if any(marker in host for marker in CLOUD_MARKERS):
        raise LocalOnlyViolation(f"Cloud inference endpoint is forbidden: {host}")
    if host in {"127.0.0.1", "localhost", "::1"}:
        return
    if allow_private_lan and _private_host(host):
        return
    raise LocalOnlyViolation(
        "LLM experiments require a loopback Ollama endpoint unless a private LAN host is explicitly enabled."
    )


def _private_host(host: str) -> bool:
    parts = host.split(".")
    if len(parts) != 4 or not all(part.isdigit() for part in parts):
        return False
    octets = [int(part) for part in parts]
    return octets[0] == 10 or (octets[0] == 192 and octets[1] == 168) or (octets[0] == 172 and 16 <= octets[1] <= 31)


class OllamaAdapter:
    def __init__(self, base_url: str, model: str, timeout_s: float = 60, allow_private_lan: bool = False):
        assert_local_endpoint(base_url, allow_private_lan=allow_private_lan)
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s

    def complete_json(self, prompt: str, schema_hint: dict) -> dict:
        if not self.model:
            raise LocalLLMUnavailable("No local model is configured.")
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": "Return one JSON object matching the requested ledger fields. Do not invent evidence identifiers."},
                {"role": "user", "content": prompt},
            ],
            "options": {"temperature": 0, "num_predict": schema_hint.get("num_predict", 800)},
        }
        request = Request(
            self.base_url + "/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_s) as response:
                body = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise LocalLLMUnavailable(f"Local model request failed: {exc}") from exc
        content = body.get("message", {}).get("content", "")
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LocalLLMUnavailable("Local model returned invalid JSON") from exc


def probe_ollama(base_url: str = "http://127.0.0.1:11434", timeout_s: float = 3) -> dict:
    assert_local_endpoint(base_url)
    request = Request(base_url.rstrip("/") + "/api/tags", method="GET")
    try:
        with urlopen(request, timeout=timeout_s) as response:
            body = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"available": False, "error": str(exc), "models": []}
    models = []
    for item in body.get("models", []):
        models.append({
            "name": item.get("name"),
            "digest": item.get("digest", "unknown"),
            "size": item.get("size"),
        })
    return {"available": True, "models": models}
