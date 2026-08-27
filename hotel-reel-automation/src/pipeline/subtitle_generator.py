"""자막 생성 모듈.

edit-plan.json(컷별 caption/duration)을 기반으로 컷별 자막을 만든다.

규칙 (요청 반영):
  - 자막은 항상 한 줄로 끝난다 (줄바꿈 없음).
  - 한 자막은 짧게 (기본 10자 안팎, 5음절 내외). 대본 문장이 이보다 길면
    문장을 통째로 줄바꿈하는 대신, 여러 개의 짧은 한 줄 자막으로 쪼개서
    그 컷이 화면에 떠 있는 시간 동안 순서대로 짧게 지나가게 한다.
    (한 Shot(컷) 하나에 SubtitleCue가 여러 개 붙을 수 있다.)

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


def _split_into_short_phrases(text: str, max_chars: int) -> list[str]:
    """긴 문장을 max_chars 이내의 짧은 한 줄 구절 여러 개로 쪼갠다.

    줄바꿈 문자(closing+cta 컷처럼 caption에 \\n이 섞여 있는 경우)는
    공백으로 취급해 이어서 짧게 쪼갠다 - 절대 두 줄짜리 자막을 만들지 않는다.
    단어(어절) 단위로 최대한 채워 넣는 greedy 방식이라, 사람이 읽기에
    자연스러운 지점에서 끊긴다.
    """
    words = text.replace("\n", " ").split(" ")
    phrases: list[str] = []
    current = ""
    for word in words:
        if not word:
            continue
        candidate = f"{current} {word}".strip()
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            phrases.append(current)
            current = word
    if current:
        phrases.append(current)
    return phrases or [text.strip()]


def _pick_emphasis_words(text: str, hints: list[str]) -> list[str]:
    return [h for h in hints if h in text]


def generate_subtitles(project: Project, shots: list[Shot], style: dict) -> list[SubtitleCue]:
    sub_config = load_subtitle_config()
    sub_style = style.get("subtitle", {})
    layout_key = sub_style.get("position", "lower_third")
    layout = sub_config["layouts"].get(layout_key, sub_config["layouts"]["lower_third"])
    hints = sub_config.get("rules", {}).get("emphasis_pos_hint", [])
    # (참고) rules.min_display_seconds는 "이상적인" 최소 노출 시간 가이드일 뿐,
    # 강제로 지키기 위해 짧은 구절들을 다시 이어붙이면 "항상 짧고 한 줄로"라는
    # 더 우선순위 높은 규칙이 깨진다. 그래서 여기서는 강제하지 않고, 컷 재생
    # 시간을 구절 길이 비율대로만 나눈다 (아래 weights 기반 분배).

    max_chars = sub_style.get("max_chars_per_line", layout["max_chars_per_line"])
    keyword_emphasis = sub_style.get("keyword_emphasis", True)

    cues: list[SubtitleCue] = []
    global_t = 0.0
    global_idx = 1
    for shot in shots:
        phrases = _split_into_short_phrases(shot.caption, max_chars)

        # 구절 수를 줄이려고 뒤 구절들을 서로 이어붙이면(예전 로직) "짧고 한 줄로"
        # 라는 규칙을 스스로 깨게 된다. 대신 컷 재생 시간을 구절 길이 비율대로
        # 나눠 쓴다 - 구절 수가 많아 1개당 시간이 min_display보다 짧아지는
        # 경우엔 그만큼 빠르게 지나가는 것을 감수한다 (문장을 억지로 뭉쳐
        # 다시 길어지는 것보다 낫다).
        weights = [max(len(p), 3) for p in phrases]
        total_weight = sum(weights)
        local_t = 0.0
        for phrase, weight in zip(phrases, weights):
            phrase_duration = shot.duration * weight / total_weight
            emphasis = _pick_emphasis_words(phrase, hints) if keyword_emphasis else []
            cues.append(SubtitleCue(
                index=global_idx,
                shot_index=shot.shot_index,
                start=global_t + local_t,
                end=global_t + local_t + phrase_duration,
                local_start=local_t,
                local_end=local_t + phrase_duration,
                lines=[phrase],
                emphasis_words=sorted(set(emphasis)),
                layout=layout_key,
            ))
            local_t += phrase_duration
            global_idx += 1

        global_t += shot.duration
    return cues


def write_subtitle_files(project: Project, cues: list[SubtitleCue]) -> None:
    write_json(project.project_dir / "subtitles.json", [c.to_dict() for c in cues])
    srt = "\n".join(c.to_srt_block() for c in cues)
    write_text(project.project_dir / "subtitles.srt", srt)
