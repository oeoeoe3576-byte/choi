"""입력 검증 유틸리티."""

from __future__ import annotations

from src.models.project import Project, VALID_LENGTHS, VALID_TONES

MIN_RECOMMENDED_IMAGES = 8


def validate_project(project: Project) -> list[str]:
    """프로젝트를 검증하고 경고 메시지 리스트를 반환한다.

    치명적 오류가 아니라면 기본값으로 보완하고 경고만 남긴다 (원칙: 실패해도 로그 남기기).
    """
    warnings: list[str] = []

    if len(project.images) == 0:
        warnings.append(
            "images/ 폴더에 이미지가 없습니다. mock 이미지를 생성하거나 사진을 추가하세요."
        )
    elif len(project.images) < MIN_RECOMMENDED_IMAGES:
        warnings.append(
            f"이미지가 {len(project.images)}장뿐입니다 (권장 {MIN_RECOMMENDED_IMAGES}장 이상). "
            "컷이 반복되거나 다양성이 떨어질 수 있습니다."
        )

    if project.video_length not in VALID_LENGTHS:
        warnings.append(
            f"video_length={project.video_length}는 지원 값이 아닙니다 "
            f"({VALID_LENGTHS}). 20초로 대체합니다."
        )
        project.video_length = 20

    if project.tone not in VALID_TONES:
        warnings.append(
            f"tone='{project.tone}'는 지원 값이 아닙니다 ({VALID_TONES}). emotional로 대체합니다."
        )
        project.tone = "emotional"

    if not project.hotel_name or project.hotel_name == "Untitled Hotel":
        warnings.append("hotel_name이 비어 있습니다. 기본값을 사용합니다.")

    if not project.highlight_points:
        warnings.append("highlight_points가 비어 있습니다. 대본 품질이 떨어질 수 있습니다.")

    return warnings
