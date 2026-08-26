"""썸네일 생성 모듈 (PIL 기반).

첫 컷 이미지를 9:16으로 크롭하고, 후킹 문구를 오버레이해 output/thumbnail.jpg를 만든다.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.models.project import Project
from src.models.shot import Shot
from src.utils.file_utils import read_json

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _find_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap(text: str, font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw, max_width: int,
          max_lines: int = 2) -> list[str]:
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)

    if len(lines) <= max_lines:
        return lines

    # 넘치는 줄은 조용히 버리지 않고, 마지막 허용 줄을 말줄임표로 잘라 표시한다.
    kept = lines[:max_lines]
    last = kept[-1]
    while last and draw.textbbox((0, 0), last + "…", font=font)[2] > max_width:
        last = last[:-1]
    kept[-1] = last.rstrip() + "…"
    return kept


def generate_thumbnail(project: Project, shots: list[Shot], hook_text: str) -> Path:
    render_cfg_path = CONFIG_DIR / "render-config.yaml"
    width, height = 1080, 1920

    first_shot = shots[0]
    image_path = project.project_dir / first_shot.image
    with Image.open(image_path) as im:
        im = im.convert("RGB")
        src_ratio = im.width / im.height
        target_ratio = width / height
        if src_ratio > target_ratio:
            new_width = int(im.height * target_ratio)
            left = (im.width - new_width) // 2
            im = im.crop((left, 0, left + new_width, im.height))
        else:
            new_height = int(im.width / target_ratio)
            top = (im.height - new_height) // 2
            im = im.crop((0, top, im.width, top + new_height))
        im = im.resize((width, height))

        draw = ImageDraw.Draw(im, "RGBA")
        font = _find_font(int(height * 0.045))
        lines = _wrap(hook_text, font, draw, max_width=int(width * 0.84), max_lines=3)

        line_height = int(height * 0.058)
        total_text_h = line_height * len(lines)
        box_top = height - int(height * 0.12) - total_text_h - 20
        box_bottom = height - int(height * 0.12) + 20
        draw.rectangle([(0, box_top), (width, box_bottom)], fill=(0, 0, 0, 110))

        y = box_top + 10
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            x = (width - text_w) / 2
            draw.text((x, y), line, font=font, fill="white",
                       stroke_width=4, stroke_fill="black")
            y += line_height

        out_path = project.output_dir / "thumbnail.jpg"
        im.save(out_path, quality=92)
        return out_path
