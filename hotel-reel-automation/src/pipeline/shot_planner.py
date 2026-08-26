"""컷(Shot) 편집 계획 생성 모듈.

script.json의 hook/scenes/closing(+cta)을 컷 단위로 쪼개고, 각 컷에 이미지를 매칭하고,
전체 영상 길이에 맞는 컷별 길이를 배분한다.

출력: edit-plan.json (motion 정보는 motion_planner가 채운 뒤 최종본이 저장됨)
"""

from __future__ import annotations

from pathlib import Path

from src.models.project import Project
from src.models.shot import Motion, Shot
from src.pipeline.image_selector import select_shot_images
from src.utils.file_utils import read_yaml, write_json
from src.utils.time_utils import distribute_durations

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


def load_style(project: Project) -> dict:
    style_rules = read_yaml(CONFIG_DIR / "style-rules.yaml")
    style_name = project.style_preset or style_rules["tone_to_style"].get(
        project.tone, style_rules["default_style"]
    )
    style = style_rules["styles"].get(style_name, style_rules["styles"][style_rules["default_style"]])
    return {"style_name": style_name, **style}


def build_shot_captions(script: dict) -> list[str]:
    """hook -> scenes -> closing+cta 순서로 컷별 자막 텍스트 리스트를 만든다."""
    captions = [script["hook"]]
    captions.extend(script["scenes"])
    closing_text = script["closing"]
    cta_text = script.get("cta", "")
    if cta_text:
        captions.append(f"{closing_text}\n{cta_text}")
    else:
        captions.append(closing_text)
    return captions


def plan_shots(project: Project, script: dict, image_analysis: list[dict]) -> tuple[list[Shot], dict]:
    style = load_style(project)
    captions = build_shot_captions(script)
    shot_count = len(captions)

    images = select_shot_images(image_analysis, shot_count)

    durations = distribute_durations(
        total=float(project.video_length),
        count=shot_count,
        first=style["first_shot_duration"],
        last=style["last_shot_duration"],
        avg=style["average_shot_duration"],
        min_d=style["min_shot_duration"],
        max_d=style["max_shot_duration"],
    )

    transition_default = style["transitions"]["default"]

    shots: list[Shot] = []
    for i, (caption, image_rec, duration) in enumerate(zip(captions, images, durations), start=1):
        shot = Shot(
            shot_index=i,
            image=image_rec["image"] if image_rec else "",
            scene_type=image_rec["scene_type"] if image_rec else "other",
            duration=duration,
            caption=caption,
            motion=Motion(),  # motion_planner가 실제 값으로 채움
            transition_in=transition_default if i > 1 else "none",
            transition_out=transition_default if i < shot_count else "none",
        )
        shots.append(shot)

    return shots, style


def write_edit_plan(project: Project, shots: list[Shot]) -> None:
    write_json(project.project_dir / "edit-plan.json", [s.to_dict() for s in shots])
