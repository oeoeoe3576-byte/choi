"""LLM 어댑터.

목적: script_generator / caption_generator가 "실제 LLM 호출"과 "오프라인 규칙 기반 생성"을
동일한 인터페이스로 쓸 수 있게 분리한다.

- ANTHROPIC_API_KEY가 환경변수에 있고 `anthropic` 패키지가 설치돼 있으면 실제 API를 호출한다.
- 그렇지 않으면 provider="stub"으로 표시하고 호출자가 자체 규칙 기반 로직으로
  폴백하도록 None을 반환한다 (MVP는 오프라인에서도 100% 동작해야 하므로 이 경로가 기본값).

이렇게 분리해두면 나중에 다른 LLM provider(OpenAI 등)를 붙일 때도
이 파일의 generate()만 교체하면 된다.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


@dataclass
class LLMResult:
    provider: str
    text: str


def is_live_provider_available() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def generate(system_prompt: str, user_prompt: str, model: str | None = None,
             max_tokens: int = 1024) -> LLMResult | None:
    """LLM 호출. 사용 불가 시 None을 반환해 호출자가 규칙 기반 폴백을 쓰도록 한다."""
    if not is_live_provider_available():
        return None

    try:
        import anthropic

        client = anthropic.Anthropic()
        model_name = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
        response = client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        return LLMResult(provider="anthropic", text=text)
    except Exception:
        # 실패 시에도 파이프라인 전체가 죽지 않도록 폴백 유도
        return None


def try_parse_json(text: str) -> dict | None:
    """LLM 응답에서 JSON 블록을 최대한 관대하게 파싱한다."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
