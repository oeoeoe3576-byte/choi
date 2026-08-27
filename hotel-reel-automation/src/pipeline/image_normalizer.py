"""이미지 정규화 모듈.

실제 숙소 사진(특히 아이폰 HEIC, 세로로 찍었지만 EXIF Orientation 태그로만
회전 정보가 남아있는 사진)을 파이프라인 나머지 단계(분류/렌더링)가 그대로
믿고 쓸 수 있는 형태로 미리 변환해둔다:

  1. HEIC/HEIF -> JPEG로 디코딩 (pillow-heif가 있으면). ffmpeg가 HEIC를
     직접 못 읽는 빌드가 많아서, 여기서 미리 변환해두지 않으면 렌더링
     단계에서 "이미지를 열 수 없음" 류의 오류로 실패한다.
  2. EXIF Orientation 태그를 실제 픽셀 회전으로 반영(exif_transpose).
     반영하지 않으면 폰으로 세로로 찍은 사진이 최종 영상에서 옆으로
     눕거나 거꾸로 나올 수 있다.
  3. RGBA/CMYK/팔레트 등 색상 모드를 RGB로 통일 (ffmpeg/후속 처리 호환성).

원본 파일은 건드리지 않고, `<project>/_normalized/`에 정규화된 JPEG 사본을
만든 뒤 그 경로들을 반환한다. 정규화에 실패한 파일은 건너뛰고 경고로
남긴다 (한 장이 깨졌다고 전체 파이프라인이 죽지 않게).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    HEIF_SUPPORTED = True
except ImportError:  # pragma: no cover - 선택 의존성
    HEIF_SUPPORTED = False

NORMALIZED_DIRNAME = "_normalized"


def normalize_images(images: list[Path], project_dir: Path) -> tuple[list[Path], list[str]]:
    """원본 이미지 목록을 정규화된 JPEG로 변환한다.

    Returns: (정규화된 이미지 경로 목록(원본과 같은 순서), 경고 메시지 목록)
    """
    if not images:
        return [], []

    out_dir = project_dir / NORMALIZED_DIRNAME
    out_dir.mkdir(parents=True, exist_ok=True)

    normalized: list[Path] = []
    warnings: list[str] = []

    for src in images:
        if src.suffix.lower() in (".heic", ".heif") and not HEIF_SUPPORTED:
            warnings.append(
                f"{src.name}: HEIC/HEIF 디코더(pillow-heif)가 설치되어 있지 않아 "
                "건너뜁니다. `pip install pillow-heif` 후 다시 실행하세요."
            )
            continue
        try:
            with Image.open(src) as im:
                im = ImageOps.exif_transpose(im)  # EXIF 회전 정보를 실제 픽셀에 반영
                if im.mode not in ("RGB",):
                    im = im.convert("RGB")
                dest = out_dir / f"{src.stem}.jpg"
                im.save(dest, format="JPEG", quality=95)
                normalized.append(dest)
        except Exception as exc:  # noqa: BLE001 - 사진 한 장이 깨졌다고 전체를 죽이지 않는다
            warnings.append(f"{src.name}: 이미지를 열 수 없어 건너뜁니다 ({exc}).")

    return normalized, warnings
