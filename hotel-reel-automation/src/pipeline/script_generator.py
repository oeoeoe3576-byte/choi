"""대본(script) 생성 모듈.

- ANTHROPIC_API_KEY가 설정돼 있으면 prompts/script-prompt.md 를 시스템 프롬프트로 사용해
  실제 LLM을 호출한다 (llm_adapter 경유).
- 그렇지 않으면 규칙 기반 템플릿으로 동일한 스키마(hook/scenes/closing/cta)를 생성한다.
  오프라인에서도 파이프라인이 100% 동작하는 것이 MVP의 핵심 요구사항이기 때문이다.

출력: script.md, script.json
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.adapters import llm_adapter
from src.models.project import Project
from src.utils.file_utils import write_text, write_json

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

SCENE_COUNT_BY_LENGTH = {15: 3, 20: 5, 30: 8}

HOOK_TEMPLATES = {
    "emotional": "{place}에서 감성 숙소 찾는다면 여기 저장해두세요.",
    "informative": "{place} 숙소 정보, 이 영상 하나로 정리했어요.",
    "review": "{place} {hotel} 실제로 묵어보고 왔어요.",
    "ad": "{hotel}, 지금 확인 안 하면 아쉬워요.",
}

CLOSING_TEMPLATES = {
    "emotional": "{place} 숙소 고민 중이라면 참고해보세요.",
    "informative": "{place} 숙소 고를 때 이 포인트들을 참고하세요.",
    "review": "직접 묵어본 솔직한 후기였어요.",
    "ad": "{hotel}, 지금이 딱 좋은 타이밍이에요.",
}

CTA_TEMPLATES = {
    "save": "저장해두고 여행 때 꺼내보세요.",
    "info": "더 궁금한 점은 댓글로 남겨주세요.",
    "comment": "궁금한 점 있으면 댓글 남겨주세요.",
    "book_now": "지금 바로 예약 링크를 확인해보세요.",
}

# 나열형 문구를 자연스러운 짧은 문장으로 바꾸기 위한 최소한의 규칙 기반 변환.
# (완벽한 한국어 NLG는 아니며, 실제 LLM 연결 시 훨씬 자연스러운 문장이 생성됩니다.)
_EXACT_SUFFIX_RULES = [
    ("적임", "적이에요"),
    ("예쁨", "예뻐요"),
    ("좋음", "좋아요"),
    ("편함", "편해요"),
    ("높음", "높아요"),
    ("쉬움", "쉬워요"),
    ("가까움", "가까워요"),
    ("깨끗함", "깨끗해요"),
    ("훌륭함", "훌륭해요"),
    ("특별함", "특별해요"),
    ("만족스러움", "만족스러워요"),
]


def _naturalize(point: str) -> str:
    point = point.strip()
    if not point:
        return point
    if point[-1] in ".!?" or point.endswith(("다", "요", "다.", "요.")):
        return point if point[-1] in ".!?" else point + "."

    for suffix, replacement in _EXACT_SUFFIX_RULES:
        if point.endswith(suffix):
            return point[: -len(suffix)] + replacement + "."

    if point.endswith("함"):
        return point[:-1] + "해요."
    if point.endswith("임"):
        return point[:-1] + "이에요."
    if point.endswith("움"):
        return point[:-1] + "워요."
    if point.endswith("음"):
        return point[:-1] + "어요."

    return point + "이에요."


def _template_script(project: Project) -> dict:
    scene_count = SCENE_COUNT_BY_LENGTH.get(project.video_length, 5)
    place = project.location or project.hotel_name
    hook = HOOK_TEMPLATES.get(project.tone, HOOK_TEMPLATES["emotional"]).format(
        place=place, hotel=project.hotel_name
    )
    closing = CLOSING_TEMPLATES.get(project.tone, CLOSING_TEMPLATES["emotional"]).format(
        place=place, hotel=project.hotel_name
    )
    cta = CTA_TEMPLATES.get(project.cta_type, CTA_TEMPLATES["save"])

    points = project.highlight_points or [f"{project.hotel_name}의 매력적인 공간"]
    scenes = []
    for i in range(scene_count):
        point = points[i % len(points)]
        scenes.append(_naturalize(point))

    return {"hook": hook, "scenes": scenes, "closing": closing, "cta": cta}


def _build_llm_prompt(project: Project) -> tuple[str, str]:
    system_prompt = (PROMPTS_DIR / "script-prompt.md").read_text(encoding="utf-8")
    user_prompt = json.dumps(
        {
            "hotel_name": project.hotel_name,
            "location": project.location,
            "one_liner": project.one_liner,
            "highlight_points": project.highlight_points,
            "price_info": project.price_info,
            "video_length": project.video_length,
            "tone": project.tone,
            "cta_type": project.cta_type,
            "extra_notes": project.extra_notes,
        },
        ensure_ascii=False,
    )
    return system_prompt, user_prompt


def generate_script(project: Project) -> tuple[dict, str]:
    """스크립트 dict와 사용된 provider("anthropic" | "template")를 반환."""
    system_prompt, user_prompt = _build_llm_prompt(project)
    result = llm_adapter.generate(system_prompt, user_prompt)
    if result is not None:
        parsed = llm_adapter.try_parse_json(result.text)
        if parsed and all(k in parsed for k in ("hook", "scenes", "closing", "cta")):
            return parsed, result.provider

    return _template_script(project), "template"


def render_script_md(project: Project, script: dict, provider: str) -> str:
    lines = [
        f"# {project.hotel_name} 릴스 대본",
        "",
        f"- 프로젝트: {project.project_name}",
        f"- 길이: {project.video_length}초 / 톤: {project.tone} / provider: {provider}",
        "",
        "## Hook",
        script["hook"],
        "",
        "## Scenes",
    ]
    for i, scene in enumerate(script["scenes"], start=1):
        lines.append(f"{i}. {scene}")
    lines += [
        "",
        "## Closing",
        script["closing"],
        "",
        "## CTA",
        script["cta"],
        "",
    ]
    return "\n".join(lines)


def run(project: Project) -> dict:
    script, provider = generate_script(project)
    write_json(project.project_dir / "script.json", {"provider": provider, **script})
    write_text(project.project_dir / "script.md", render_script_md(project, script, provider))
    return script
