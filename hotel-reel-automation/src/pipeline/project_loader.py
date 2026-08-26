"""프로젝트 폴더를 읽어 Project 객체를 구성한다.

input.md / input.yaml / input.json 중 존재하는 파일을 읽는다.
input.md는 아래처럼 'key: value' 형태의 YAML-like front matter를 그대로 YAML로 파싱한다
(프롬프트 예시의 input.md가 사실상 YAML 문법이므로 yaml.safe_load로 바로 처리 가능).
"""

from __future__ import annotations

from pathlib import Path

from src.models.project import Project
from src.utils.file_utils import ensure_dir, list_images, read_yaml, read_json
from src.utils.validators import validate_project

INPUT_FILE_CANDIDATES = ["input.md", "input.yaml", "input.yml", "input.json"]


def _load_raw_input(project_dir: Path) -> dict:
    for name in INPUT_FILE_CANDIDATES:
        path = project_dir / name
        if not path.exists():
            continue
        if name.endswith(".json"):
            return read_json(path) or {}
        # input.md 도 YAML 문법(key: value, - list) 이므로 동일하게 파싱
        return read_yaml(path) or {}
    return {}


def load_project(project_dir: str | Path) -> Project:
    project_dir = Path(project_dir).resolve()
    if not project_dir.exists():
        raise FileNotFoundError(f"프로젝트 폴더를 찾을 수 없습니다: {project_dir}")

    raw = _load_raw_input(project_dir)

    project = Project(
        project_dir=project_dir,
        project_name=str(raw.get("project_name", project_dir.name)),
        hotel_name=str(raw.get("hotel_name", "Untitled Hotel")),
        location=str(raw.get("location", "")),
        one_liner=str(raw.get("one_liner", raw.get("intro", ""))),
        video_length=int(raw.get("video_length", 20)),
        tone=str(raw.get("tone", "emotional")),
        style_preset=str(raw.get("style_preset", "")),
        cta_type=str(raw.get("cta_type", "save")),
        price_info=str(raw.get("price_info", "")),
        highlight_points=list(raw.get("highlight_points", []) or []),
        extra_notes=list(raw.get("extra_notes", []) or []),
    )

    project.images = list_images(project.images_dir)

    ref_dir = project.references_dir
    project.reference_dir = ref_dir if ref_dir.exists() else None

    ensure_dir(project.output_dir)
    ensure_dir(project.logs_dir)

    project.warnings = validate_project(project)

    return project


def apply_overrides(project: Project, tone: str | None = None, length: int | None = None) -> Project:
    if tone:
        project.tone = tone
    if length:
        project.video_length = length
    return project
