"""자막 생성 모듈.

edit-plan.json(컷별 caption/duration)을 기반으로 컷별 시작/종료 타이밍을 계산하고,
subtitle-template.yaml의 레이아웃 규칙에 맞춰 줄바꿈 및 키워드 강조를 적용한다.

출력: subtitles.json, subtitles.srt
"""

from __future__ import annotations

from pathlib import Path

from src.models.project import Project
from src.models.shot import Shot
from src.models.subtitle import SubtitleCue
from src.utils.file_utils import read_yaml, write_json, write_text

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


def load_subtitle_config() -> dict:
    return read_yaml(CONFIG_DIR / "subtitle-template.yaml")


def _wrap_text(text: str, max_chars: int, max_lines: int) -> list[str]:
    """자막 텍스트를 max_chars_per_line/max_lines 규칙에 맞춰 줄바꿈한다.

    caption에 이미 개행이 포함돼 있으면(closing+cta 컷처럼) 그 줄바꿈을 우선 존중한다.
    """
    if "\n" in text:
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        return lines[:max_lines]

    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)

    if len(lines) > max_lines:
        # max_lines를 넘기는 초과분은 버리지 않고 마지막 허용 줄에 이어붙인다
        # (자막이 화면 밖으로 밀려도, 문장을 통째로 잃어버리는 것보다 낫다)
        kept = lines[:max_lines]
        overflow = " ".join(lines[max_lines:])
        kept[-1] = f"{kept[-1]} {overflow}".strip()
        lines = kept
    return lines


def _pick_emphasis_words(text: str, hints: list[str]) -> list[str]:
    return [h for h in hints if h in text]


def generate_subtitles(project: Project, shots: list[Shot], style: dict) -> list[SubtitleCue]:
    sub_config = load_subtitle_config()
    layout_key = style.get("subtitle", {}).get("position", "lower_third")
    layout = sub_config["layouts"].get(layout_key, sub_config["layouts"]["lower_third"])
    hints = sub_config.get("rules", {}).get("emphasis_pos_hint", [])

    max_lines = style.get("subtitle", {}).get("max_lines", layout["max_lines"])
    max_chars = style.get("subtitle", {}).get("max_chars_per_line", layout["max_chars_per_line"])

    cues: list[SubtitleCue] = []
    t = 0.0
    for shot in shots:
        start = t
        end = t + shot.duration
        lines = _wrap_text(shot.caption, max_chars, max_lines)
        emphasis = []
        if style.get("subtitle", {}).get("keyword_emphasis", True):
            for line in lines:
                emphasis.extend(_pick_emphasis_words(line, hints))
        cues.append(SubtitleCue(
            index=shot.shot_index,
            start=start,
            end=end,
            lines=lines,
            emphasis_words=sorted(set(emphasis)),
            layout=layout_key,
        ))
        t = end
    return cues


def write_subtitle_files(project: Project, cues: list[SubtitleCue]) -> None:
    write_json(project.project_dir / "subtitles.json", [c.to_dict() for c in cues])
    srt = "\n".join(c.to_srt_block() for c in cues)
    write_text(project.project_dir / "subtitles.srt", srt)
