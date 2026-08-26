"""이미지 모션 플래너.

각 컷의 scene_type에 따라 style-rules.yaml의 motion_preferences 순서와
motion-presets.yaml의 실제 파라미터를 결합해 모션을 배정한다.

규칙(설계 원칙 반영):
  - 과한 줌/빠른 이동 금지 -> motion-presets.yaml의 global_limits를 항상 준수
  - 같은 모션이 연속되지 않도록 우선순위 리스트에서 순환 선택
  - 슬라이드쇼처럼 보이지 않도록 항상 약한 움직임을 부여 (정지 모션 없음)

출력: motion-plan.json (+ Shot.motion 필드를 채워서 반환)
그리고 각 컷에 대해 image_to_video_adapter로 AI 영상화 적용 여부도 함께 기록한다
(2차 확장 포인트, MVP에서는 기본 비활성화).
"""

from __future__ import annotations

from pathlib import Path

from src.adapters import image_to_video_adapter
from src.models.project import Project
from src.models.shot import Motion, Shot
from src.utils.file_utils import read_yaml, write_json

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


def load_motion_presets() -> dict:
    return read_yaml(CONFIG_DIR / "motion-presets.yaml")


def assign_motions(shots: list[Shot], style: dict, image_to_video_enabled: bool = False) -> list[dict]:
    presets = load_motion_presets()
    limits = presets["global_limits"]
    preset_defs = presets["presets"]
    motion_prefs = style.get("motion_preferences", {})
    fallback_order = presets.get("fallback_order", ["zoom_in"])

    last_preset_name = None
    plan_records = []

    for shot in shots:
        candidates = motion_prefs.get(shot.scene_type) or motion_prefs.get("default") or fallback_order
        # 직전 컷과 동일한 모션 프리셋이 연속되지 않도록 회피
        chosen_name = candidates[0]
        for candidate in candidates:
            if candidate != last_preset_name:
                chosen_name = candidate
                break

        preset = preset_defs.get(chosen_name, preset_defs["zoom_in"])

        start_scale = preset.get("start_scale", 1.0)
        end_scale = preset.get("end_scale", preset.get("scale", 1.1))
        start_scale = min(start_scale, limits["max_zoom"])
        end_scale = min(end_scale, limits["max_zoom"])
        if abs(end_scale - start_scale) < (limits["min_zoom_delta"] - 1.0):
            end_scale = min(start_scale + (limits["min_zoom_delta"] - 1.0), limits["max_zoom"])

        travel_pct = min(preset.get("travel_pct", 0), limits["max_pan_pct"])

        shot.motion = Motion(
            preset=chosen_name,
            start_scale=round(start_scale, 4),
            end_scale=round(end_scale, 4),
            direction=preset.get("direction", "in"),
            travel_pct=travel_pct,
        )

        decision = image_to_video_adapter.decide(shot.scene_type, enabled=image_to_video_enabled)

        plan_records.append({
            "shot_index": shot.shot_index,
            "scene_type": shot.scene_type,
            "motion": chosen_name,
            "start_scale": shot.motion.start_scale,
            "end_scale": shot.motion.end_scale,
            "direction": shot.motion.direction,
            "travel_pct": shot.motion.travel_pct,
            "image_to_video": {
                "use_image_to_video": decision.use_image_to_video,
                "provider": decision.provider,
                "reason": decision.reason,
            },
        })

        last_preset_name = chosen_name

    return plan_records


def write_motion_plan(project: Project, plan_records: list[dict]) -> None:
    write_json(project.project_dir / "motion-plan.json", plan_records)
