"""컷(Shot) 단위 편집 계획 데이터 모델."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Motion:
    preset: str = "zoom_in"
    start_scale: float = 1.0
    end_scale: float = 1.14
    direction: str = "in"
    travel_pct: float = 0.0


@dataclass
class Shot:
    shot_index: int
    image: str                     # 프로젝트 폴더 기준 상대경로, 예: images/01.jpg
    scene_type: str = "other"
    duration: float = 1.5
    caption: str = ""              # 이 컷에 매칭된 자막(대본 문장)
    motion: Motion = field(default_factory=Motion)
    transition_in: str = "fade"
    transition_out: str = "fade"

    def to_dict(self) -> dict:
        return {
            "shot_index": self.shot_index,
            "image": self.image,
            "scene_type": self.scene_type,
            "duration": round(self.duration, 3),
            "caption": self.caption,
            "motion": {
                "preset": self.motion.preset,
                "start_scale": self.motion.start_scale,
                "end_scale": self.motion.end_scale,
                "direction": self.motion.direction,
                "travel_pct": self.motion.travel_pct,
            },
            "transition_in": self.transition_in,
            "transition_out": self.transition_out,
        }
