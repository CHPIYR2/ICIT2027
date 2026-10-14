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
    raw: dict = field(repr=False, default_factory=dict)
    model: str = ""
    done_reason: str = ""
    truncated: bool = False
    thinking: str = ""


class OllamaClient:
    def __init__(self, model: str, *, endpoint: str = "http://127.0.0.1:11434", timeout: int = 180):
        self.model = model
        self.model_name = model
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def chat(self, messages: list[dict], *, tools=None, temperature: float = 0.0,
             seed: int = 1, num_predict: int = 700, require_tool: bool = False,
             think: bool = False, response_format: dict | None = None) -> LLMTurn:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": think,
            "options": {"temperature": temperature, "seed": seed, "num_predict": num_predict},
        }
        if tools:
            payload["tools"] = tools
            if require_tool:
                payload["tool_choice"] = "required"
        if response_format is not None:
            payload["format"] = response_format
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
        thinking = message.get("thinking") or ""
        if isinstance(thinking, list):
            thinking = "".join(str(part) for part in thinking)
        completion = int(body.get("eval_count") or 0)
        reason = str(body.get("done_reason") or "")
        return LLMTurn(
            content=str(content), tool_calls=calls,
            prompt_tokens=int(body.get("prompt_eval_count") or 0),
            completion_tokens=completion,
            raw={"done_reason": reason, "eval_count": completion,
                 "prompt_eval_count": int(body.get("prompt_eval_count") or 0),
                 "message_keys": sorted(message.keys()),
                 "thinking_chars": len(str(thinking)), "content_chars": len(str(content))},
            model=self.model, done_reason=reason,
            truncated=reason == "length" or (num_predict > 0 and completion >= num_predict and reason != "stop"),
            thinking=str(thinking),
        )

    def probe_tool_choice(self) -> dict:
        """Ask the server whether tool_choice is accepted. A 200 does not mean the model called a tool."""
        version = ""
        try:
            request = urllib.request.Request(self.endpoint + "/api/version")
            with urllib.request.urlopen(request, timeout=10) as response:
                version = json.loads(response.read().decode("utf-8")).get("version", "")
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
            return {"version": version, "server_accepts_tool_choice": False, "probe_error": str(exc),
                    "model_returned_tool_call": False}
        payload = {
            "model": self.model, "stream": False, "think": False,
            "messages": [{"role": "user", "content": "Call the tool with limit 1."}],
            "tools": [{"type": "function", "function": {
                "name": "query_tcp_flows", "description": "List flows",
                "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}, "required": ["limit"]},
            }}],
            "tool_choice": "required",
            "options": {"temperature": 0, "num_predict": 40},
        }
        try:
            body = self._post(payload)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            return {"version": version, "server_accepts_tool_choice": False, "http_status": exc.code,
                    "probe_error": detail, "model_returned_tool_call": False}
        calls = (body.get("message") or {}).get("tool_calls") or []
        return {"version": version, "server_accepts_tool_choice": True, "http_status": 200,
                "model_returned_tool_call": bool(calls),
                "note": "Accepting the field does not guarantee later investigation turns will call a tool."}

    def _post(self, payload: dict) -> dict:
        request = urllib.request.Request(
            self.endpoint + "/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))
