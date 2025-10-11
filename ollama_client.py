import json
import os
import re
from typing import Any, Dict, List, Optional, Type, Union

from openai import OpenAI
from pydantic import BaseModel, ValidationError


class OllamaError(RuntimeError):
    """Raised when the Ollama API returns an unexpected response."""


class OllamaLLM:
    """Thin wrapper over Ollama's OpenAI-compatible endpoint."""

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        request_timeout: float = 120.0,
    ):
        self.model = model
        self.temperature = temperature
        raw_base_url = base_url or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
        trimmed = raw_base_url.rstrip("/")
        self.base_url = trimmed if trimmed.endswith("/v1") else f"{trimmed}/v1"
        self.api_key = api_key or os.environ.get("OLLAMA_API_KEY") or "ollama"
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=request_timeout,
        )

    def with_structured_output(self, schema: Type[BaseModel]):
        return _StructuredOpenAIRunnable(self, schema)

    def chat(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._completion(messages)

    def _completion(self, messages: List[Dict[str, str]]) -> str:
        result = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )
        if not result.choices:
            raise OllamaError("Ollama returned no choices.")
        message = result.choices[0].message
        if message is None:
            raise OllamaError("Ollama response missing message.")
        content = message.content
        if isinstance(content, list):
            chunks = [part.get("text", "") for part in content if isinstance(part, dict)]
            content = "".join(chunks)
        if not isinstance(content, str):
            raise OllamaError(f"Unexpected response payload: {content!r}")
        return content


class _StructuredOpenAIRunnable:
    def __init__(self, client: OllamaLLM, schema: Type[BaseModel]):
        self.client = client
        self.schema = schema
        schema_dict = self._get_schema_dict(schema)
        schema_json = json.dumps(schema_dict, indent=2, ensure_ascii=False)
        self.system_prompt = (
            "Respond strictly with JSON matching this schema.\n"
            f"{schema_json}\n"
            "No extra text or markdown."
        )

    def invoke(self, prompt: Union[str, List[Any]]) -> BaseModel:
        messages = self._build_messages(prompt)
        raw = self.client._completion(messages)
        data = self._parse_json(raw)
        try:
            return self.schema(**data)
        except ValidationError as exc:
            raise OllamaError(f"Failed to validate Ollama response: {exc}") from exc

    def _build_messages(self, prompt: Union[str, List[Any]]) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": self.system_prompt}]
        if isinstance(prompt, str):
            messages.append({"role": "user", "content": prompt})
        elif isinstance(prompt, list):
            for item in prompt:
                messages.append(self._coerce_message(item))
        else:
            raise TypeError("Prompt must be a string or list of messages.")
        return messages

    def _coerce_message(self, item: Any) -> Dict[str, str]:
        if isinstance(item, dict):
            role = item.get("role", "user")
            content = item.get("content")
        else:
            role = getattr(item, "type", getattr(item, "role", "user"))
            content = getattr(item, "content", str(item))
        if not isinstance(content, str):
            raise TypeError("Message content must be a string.")
        return {"role": role, "content": content}

    def _parse_json(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError as exc:
                    raise OllamaError(f"Ollama returned invalid JSON: {text}") from exc
        raise OllamaError(f"Ollama response was not valid JSON: {text}")

    @staticmethod
    def _get_schema_dict(schema: Type[BaseModel]) -> Dict[str, Any]:
        try:
            return schema.model_json_schema()  # Pydantic v2
        except AttributeError:
            return schema.schema()  # Pydantic v1
