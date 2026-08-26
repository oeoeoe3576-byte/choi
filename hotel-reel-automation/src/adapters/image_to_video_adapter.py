"""AI Image-to-Video 확장 포인트.

모든 이미지를 AI로 영상화하는 게 아니라, 특정 장면(수영장 물결, 커튼 흔들림 등)만
선별적으로 image-to-video 처리하기 위한 인터페이스.

MVP에서는 provider="stub"로 동작하며 실제 변환은 하지 않는다 (motion_planner가
정적 이미지 + zoompan 모션으로 대체 처리). 나중에 실제 provider(Runway, Kling,
Luma 등)를 붙일 때 `convert()`만 구현하면 된다.
"""

from __future__ import annotations

from dataclasses import dataclass

# 이 태그들은 image-to-video로 넘기면 효과가 좋은 장면 유형 (2차 확장 시 사용)
BENEFICIAL_SCENE_TYPES = {
    "pool": "수영장 물결 움직임 표현에 유리",
    "night_view": "야경 조명/반짝임 표현에 유리",
    "terrace": "커튼/바람 표현에 유리",
    "view": "구름/바다 움직임 표현에 유리",
}


@dataclass
class ImageToVideoDecision:
    use_image_to_video: bool
    provider: str
    reason: str


def decide(scene_type: str, enabled: bool = False) -> ImageToVideoDecision:
    """해당 scene_type에 image-to-video를 적용할지 결정한다.

    MVP 기본값(enabled=False)에서는 항상 False를 반환해 정적 이미지 + 모션 경로를 쓴다.
    """
    if not enabled:
        return ImageToVideoDecision(False, "stub", "image_to_video disabled in MVP config")

    if scene_type in BENEFICIAL_SCENE_TYPES:
        return ImageToVideoDecision(True, "stub", BENEFICIAL_SCENE_TYPES[scene_type])

    return ImageToVideoDecision(False, "stub", f"scene_type '{scene_type}' does not benefit from motion synthesis")


def convert(image_path: str, scene_type: str) -> str:
    """실제 image-to-video 변환 스텁. provider 연결 전까지는 NotImplementedError."""
    raise NotImplementedError(
        "image_to_video_adapter.convert()는 아직 구현되지 않았습니다. "
        "실제 provider(API)를 연결한 뒤 이 함수를 구현하세요."
    )
