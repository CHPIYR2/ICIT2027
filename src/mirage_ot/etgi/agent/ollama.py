"""Local Ollama client. One model is called at a time."""
from __future__ import annotations
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field


@dataclass
class LLMTurn:
    content: str
    tool_calls: list[dict]
    prompt_tokens: int
    completion_tokens: int
    raw: dict = field(repr=False)
    model: str = ""


class OllamaClient:
    def __init__(self, model: str, *, endpoint: str = "http://127.0.0.1:11434", timeout: int = 180):
        self.model = model
        self.model_name = model
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def chat(self, messages: list[dict], *, tools=None, temperature: float = 0.0,
             seed: int = 1, num_predict: int = 700, require_tool: bool = False) -> LLMTurn:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {"temperature": temperature, "seed": seed, "num_predict": num_predict},
        }
        if tools:
            payload["tools"] = tools
            if require_tool:
                payload["tool_choice"] = "required"
        try:
            body = self._post(payload)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            if "think" in detail.lower() or exc.code == 400:
                payload.pop("think", None)
                body = self._post(payload)
            else:
                raise RuntimeError(f"Ollama HTTP {exc.code}: {detail}") from exc
        message = body.get("message") or {}
        calls = []
        for call in message.get("tool_calls") or []:
            function = call.get("function") or call
            arguments = function.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {"_unparsed": arguments}
            calls.append({"name": function.get("name"), "arguments": arguments, "id": call.get("id")})
        content = message.get("content") or ""
        if isinstance(content, list):
            content = "".join(str(part) for part in content)
        return LLMTurn(
            content=str(content), tool_calls=calls,
            prompt_tokens=int(body.get("prompt_eval_count") or 0),
            completion_tokens=int(body.get("eval_count") or 0),
            raw=body, model=self.model,
        )

    def _post(self, payload: dict) -> dict:
        request = urllib.request.Request(
            self.endpoint + "/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))
