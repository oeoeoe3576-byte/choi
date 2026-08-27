#!/usr/bin/env python3
"""실제 숙소 사진이 없을 때 파이프라인 구조를 테스트하기 위한 mock 이미지 생성기.

사용법:
  python3 scripts/generate_mock_images.py --project sample_projects/sample_hotel

파일명에 scene_type 키워드를 넣어 image_classifier.py가 올바르게 분류하도록 한다.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

# (파일명, 기본 배경색, 밝은 보조색) - image_classifier.py가 파일명으로 scene_type을
# 인식하도록 이름에 키워드를 넣는다. 실제 영상에 섞여 보이면 안 되므로 이미지 위에는
# 아무 글자도 쓰지 않고, 은은한 그라데이션 블록만 사용한다 (모션/자막 테스트용).
SCENES = [
    ("01_exterior", (58, 90, 120)),
    ("02_lobby", (120, 100, 80)),
    ("03_room_wide", (150, 130, 110)),
    ("04_bed", (170, 150, 140)),
    ("05_bathroom", (200, 210, 215)),
    ("06_view", (70, 130, 160)),
    ("07_terrace", (110, 140, 100)),
    ("08_pool", (40, 130, 150)),
    ("09_breakfast", (200, 160, 90)),
    ("10_detail", (130, 110, 140)),
    ("11_night_view", (30, 30, 60)),
    ("12_view", (200, 120, 80)),
]


def _gradient_block(width: int, height: int, base: tuple[int, int, int], seed: int) -> Image.Image:
    """텍스트 없이, 컷마다 살짝 다른 대각선 그라데이션 블록을 만든다.

    완전 단색이면 화면이 다 똑같아 보여 모션 확인이 어려우므로 최소한의
    시각적 변화만 준다 (실제 사진을 넣으면 이 mock 생성기는 필요 없다).
    """
    rng = random.Random(seed)
    lighten = rng.randint(20, 45)
    light = tuple(min(255, c + lighten) for c in base)
    img = Image.new("RGB", (width, height), base)
    overlay = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(overlay)
    draw.polygon([(0, height), (width * 0.6, 0), (width, 0), (width, height)], fill=180)
    overlay = overlay.filter(ImageFilter.GaussianBlur(width * 0.15))
    solid = Image.new("RGB", (width, height), light)
    img = Image.composite(solid, img, overlay)
    return img


def generate(project_dir: Path, count: int, width: int, height: int) -> list[Path]:
    images_dir = project_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    created = []
    for i in range(count):
        name, color = SCENES[i % len(SCENES)]
        suffix = "" if i < len(SCENES) else f"_{i}"
        img = _gradient_block(width, height, color, seed=i)
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
