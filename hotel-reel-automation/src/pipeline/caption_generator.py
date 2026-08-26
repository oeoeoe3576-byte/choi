"""인스타그램 캡션 생성 모듈.

script.json을 바탕으로 [후킹형] / [정보형] / [해시태그] 3종 캡션을 생성한다.
ANTHROPIC_API_KEY가 있으면 LLM으로, 없으면 규칙 기반 템플릿으로 생성한다.

출력: caption.txt
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.adapters import llm_adapter
from src.models.project import Project
from src.pipeline.script_generator import _naturalize
from src.utils.file_utils import write_text

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

STOPWORDS = {"그리고", "정말", "매우", "너무", "아주", "그", "이", "저"}

# 해시태그로 쓰기엔 어색한 조사(체언 뒤에 자주 붙는 것들)를 토큰 끝에서 제거한다.
# 완벽한 형태소 분석은 아니지만, MVP 수준에서 "뷰가" -> "뷰"처럼 다듬어준다.
_TRAILING_PARTICLES = ("이가", "가", "이", "은", "는", "을", "를", "의", "도", "만")


def _strip_trailing_particle(token: str) -> str:
    if len(token) <= 1:
        return token
    for particle in _TRAILING_PARTICLES:
        if token.endswith(particle) and len(token) - len(particle) >= 1:
            return token[: -len(particle)]
    return token


def _keywords_from_text(*texts: str, limit: int = 6) -> list[str]:
    joined = " ".join(texts)
    tokens = re.findall(r"[가-힣A-Za-z0-9]{2,}", joined)
    seen: list[str] = []
    for tok in tokens:
        tok = _strip_trailing_particle(tok)
        if tok in STOPWORDS or tok in seen or len(tok) < 2:
            continue
        seen.append(tok)
        if len(seen) >= limit:
            break
    return seen


def _template_caption(project: Project, script: dict) -> str:
    place = re.sub(r"[^0-9A-Za-z가-힣]", "", project.location or "")
    hotel_short = re.sub(r"\s+", "", project.hotel_name)

    hook_lines = [script["hook"], script["scenes"][0] if script["scenes"] else project.one_liner]
    natural_points = [_naturalize(p).rstrip(".") for p in project.highlight_points[:3]]
    info_lines = [
        (f"{project.hotel_name}은(는) " + ", ".join(natural_points) + " 숙소예요.")
        if natural_points else project.one_liner,
        script["closing"],
    ]
    if project.price_info:
        info_lines.append(f"가격대: {project.price_info}")

    base_tags = []
    if place:
        base_tags.append(f"#{place}숙소")
        base_tags.append(f"#{place}여행")
    base_tags.append(f"#{hotel_short}")
    base_tags += [f"#{kw}" for kw in _keywords_from_text(*project.highlight_points)]
    base_tags += ["#여행스타그램", "#숙소추천", "#감성숙소", "#릴스"]
    # 중복 제거, 순서 유지
    seen_tags: list[str] = []
    for tag in base_tags:
        if tag not in seen_tags:
            seen_tags.append(tag)
    hashtags = " ".join(seen_tags[:12])

    return (
        "[후킹형]\n" + "\n".join(l for l in hook_lines if l) + "\n\n"
        "[정보형]\n" + "\n".join(l for l in info_lines if l) + "\n\n"
        "[해시태그]\n" + hashtags + "\n"
    )


def generate_caption(project: Project, script: dict) -> tuple[str, str]:
    system_prompt = (PROMPTS_DIR / "caption-prompt.md").read_text(encoding="utf-8")
    user_prompt = json.dumps(
        {
            "hotel_name": project.hotel_name,
            "location": project.location,
            "one_liner": project.one_liner,
            "highlight_points": project.highlight_points,
            "price_info": project.price_info,
            "tone": project.tone,
            "script": script,
        },
        ensure_ascii=False,
    )
    result = llm_adapter.generate(system_prompt, user_prompt)
    if result is not None and "[후킹형]" in result.text:
        return result.text.strip() + "\n", result.provider
    return _template_caption(project, script), "template"


def run(project: Project, script: dict) -> str:
    caption_text, provider = generate_caption(project, script)
    write_text(project.project_dir / "caption.txt", caption_text)
    return caption_text
