"""프로젝트 입력(input.md/yaml/json)을 표현하는 데이터 모델."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


VALID_TONES = ("emotional", "informative", "review", "ad")
VALID_LENGTHS = (15, 20, 30)


@dataclass
class Project:
    """숙소 릴스 프로젝트 하나에 대한 입력 메타데이터 + 경로 정보."""

    project_dir: Path
    project_name: str = "untitled-reel"
    hotel_name: str = "Untitled Hotel"
    location: str = ""
    one_liner: str = ""
    video_length: int = 20
    tone: str = "emotional"
    style_preset: str = ""
    cta_type: str = "save"
    price_info: str = ""
    highlight_points: list[str] = field(default_factory=list)
    extra_notes: list[str] = field(default_factory=list)

    # 실행 시 채워지는 필드
    images: list[Path] = field(default_factory=list)
    reference_dir: Path | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def images_dir(self) -> Path:
        return self.project_dir / "images"

    @property
    def references_dir(self) -> Path:
        return self.project_dir / "references"

    @property
    def output_dir(self) -> Path:
        return self.project_dir / "output"

    @property
    def logs_dir(self) -> Path:
        return self.project_dir / "logs"

    def as_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "hotel_name": self.hotel_name,
            "location": self.location,
            "one_liner": self.one_liner,
            "video_length": self.video_length,
            "tone": self.tone,
            "style_preset": self.style_preset,
            "cta_type": self.cta_type,
            "price_info": self.price_info,
            "highlight_points": self.highlight_points,
            "extra_notes": self.extra_notes,
        }
