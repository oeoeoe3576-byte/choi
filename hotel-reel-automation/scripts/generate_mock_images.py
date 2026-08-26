#!/usr/bin/env python3
"""실제 숙소 사진이 없을 때 파이프라인 구조를 테스트하기 위한 mock 이미지 생성기.

사용법:
  python3 scripts/generate_mock_images.py --project sample_projects/sample_hotel

파일명에 scene_type 키워드를 넣어 image_classifier.py가 올바르게 분류하도록 한다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCENES = [
    ("01_exterior", "EXTERIOR", (58, 90, 120)),
    ("02_lobby", "LOBBY", (120, 100, 80)),
    ("03_room_wide", "ROOM", (150, 130, 110)),
    ("04_bed", "BED", (170, 150, 140)),
    ("05_bathroom", "BATHROOM", (200, 210, 215)),
    ("06_view", "RIVER VIEW", (70, 130, 160)),
    ("07_terrace", "TERRACE", (110, 140, 100)),
    ("08_pool", "POOL", (40, 130, 150)),
    ("09_breakfast", "BREAKFAST", (200, 160, 90)),
    ("10_detail", "DETAIL", (130, 110, 140)),
    ("11_night_view", "NIGHT VIEW", (30, 30, 60)),
    ("12_view", "SUNSET VIEW", (200, 120, 80)),
]

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _font(size: int):
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def generate(project_dir: Path, count: int, width: int, height: int) -> list[Path]:
    images_dir = project_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    font = _font(64)
    created = []
    for i in range(count):
        name, label, color = SCENES[i % len(SCENES)]
        suffix = "" if i < len(SCENES) else f"_{i}"
        img = Image.new("RGB", (width, height), color)
        draw = ImageDraw.Draw(img)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((width - tw) / 2, (height - th) / 2), label, font=font, fill="white",
                   stroke_width=3, stroke_fill="black")
        out_path = images_dir / f"{name}{suffix}.jpg"
        img.save(out_path, quality=90)
        created.append(out_path)
    return created


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="프로젝트 폴더 경로")
    parser.add_argument("--count", type=int, default=12, help="생성할 이미지 수 (기본 12)")
    parser.add_argument("--width", type=int, default=1600, help="mock 이미지 가로 크기")
    parser.add_argument("--height", type=int, default=1067, help="mock 이미지 세로 크기 (기본 3:2 가로 사진 흉내)")
    args = parser.parse_args()

    project_dir = Path(args.project).resolve()
    created = generate(project_dir, args.count, args.width, args.height)
    print(f"{len(created)}장의 mock 이미지를 생성했습니다: {project_dir / 'images'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
