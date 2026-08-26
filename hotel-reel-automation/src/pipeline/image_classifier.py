"""이미지 분류/태깅 모듈.

MVP 구현: 파일명 키워드 기반 규칙 분류 + 정교한 모델이 없을 때의 안전한 폴백
(라운드로빈 분배)으로 동작한다. `classify_with_vision()`은 비전 모델을 붙였을 때
쓸 수 있는 확장 스텁이다 (prompts/image-tagging-prompt.md 참고).

출력: image-analysis.json 형태의 dict 리스트.
"""

from __future__ import annotations

from pathlib import Path

# 파일명에 포함되면 해당 scene_type으로 분류하는 키워드 규칙 (우선순위 순서)
FILENAME_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("exterior", ("exterior", "outside", "ext", "facade", "건물", "외관")),
    ("lobby", ("lobby", "reception", "로비")),
    ("night_view", ("night", "야경")),   # "night_view"가 "view"보다 먼저 매칭되도록 순서상 위에 둔다
    ("bed", ("bed", "bedroom", "침대", "객실")),
    ("bathroom", ("bath", "toilet", "shower", "욕실", "화장실")),
    ("pool", ("pool", "swim", "수영장")),
    ("breakfast", ("breakfast", "food", "dining", "조식", "식사")),
    ("terrace", ("terrace", "balcony", "테라스", "발코니")),
    ("view", ("view", "riverside", "ocean", "sea", "뷰", "전망")),
    ("room_wide", ("room", "interior", "living", "인테리어", "거실")),
    ("detail", ("detail", "amenity", "디테일", "소품")),
]

# 이미지에 아무 키워드도 없을 때 순환 배정할 기본 태그 순서
FALLBACK_ROTATION = (
    "exterior", "room_wide", "bed", "view", "bathroom",
    "terrace", "pool", "breakfast", "lobby", "detail",
)

# 영상 흐름상 자연스러운 등장 우선순위 (낮을수록 먼저 노출하기 좋음)
NARRATIVE_PRIORITY = {
    "exterior": 0,
    "lobby": 1,
    "room_wide": 2,
    "view": 3,
    "terrace": 4,
    "bed": 5,
    "bathroom": 6,
    "pool": 7,
    "breakfast": 8,
    "night_view": 9,
    "detail": 10,
    "other": 11,
}


def _classify_by_filename(name: str) -> str | None:
    lowered = name.lower()
    for scene_type, keywords in FILENAME_KEYWORDS:
        if any(kw in lowered for kw in keywords):
            return scene_type
    return None


def _quality_score(image_path: Path) -> int:
    """정교한 CV 없이 파일 크기 기반의 단순 휴리스틱 점수 (0~100).

    지나치게 작은 파일(저해상도 가능성)에 페널티를 준다.
    """
    try:
        size_kb = image_path.stat().st_size / 1024
    except OSError:
        return 50
    if size_kb < 30:
        return 40
    if size_kb < 100:
        return 60
    if size_kb < 300:
        return 80
    return 90


def classify_images(images: list[Path], project_dir: Path) -> list[dict]:
    """이미지 목록을 분류해 image-analysis.json에 저장할 레코드 리스트를 반환."""
    results = []
    fallback_idx = 0
    for i, img in enumerate(images):
        scene_type = _classify_by_filename(img.name)
        if scene_type is None:
            scene_type = FALLBACK_ROTATION[fallback_idx % len(FALLBACK_ROTATION)]
            fallback_idx += 1
            method = "fallback_rotation"
        else:
            method = "filename_keyword"

        rel_path = str(img.relative_to(project_dir))
        results.append({
            "image": rel_path,
            "scene_type": scene_type,
            "quality_score": _quality_score(img),
            "narrative_priority": NARRATIVE_PRIORITY.get(scene_type, 11),
            "classification_method": method,
            "order_in_folder": i,
        })
    return results


def classify_with_vision(images: list[Path]) -> list[dict]:  # pragma: no cover - 확장 스텁
    """비전 모델 기반 분류 확장 포인트. 아직 미구현.

    prompts/image-tagging-prompt.md 를 llm_adapter.generate()에 이미지와 함께
    전달하도록 구현하면 된다.
    """
    raise NotImplementedError(
        "classify_with_vision()은 아직 구현되지 않았습니다. "
        "비전 지원 LLM 연결 시 이 함수를 채워 classify_images()를 대체하세요."
    )
