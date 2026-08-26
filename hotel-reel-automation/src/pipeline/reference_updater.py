"""레퍼런스 영상 규칙 업데이트 모듈 (2차 확장 포인트의 MVP 버전).

--update-style-rules --reference-dir <path> 실행 시 호출된다.

MVP 동작:
  - references/ 폴더에서 `notes.yaml`(사람이 정리한 규칙)이 있으면 읽어서
    style-rules.yaml의 해당 style_name에 병합(merge)한다.
  - notes.yaml이 없으면, references/ 폴더 안의 파일 목록만 훑어서
    reference_notes에 "아직 미분석" 기록을 남긴다 (완전 자동 분석은 2차 확장).

notes.yaml 예시 (references/notes.yaml):
  style_name: clean_travel
  average_shot_duration: 1.3
  first_shot_duration: 1.6
  transitions:
    default: fade
  subtitle:
    position: lower_third
    max_lines: 2
  motion_preferences:
    exterior: [zoom_in, slow_drift]
  hook_pattern: "3초 안에 뷰 컷 먼저 보여주기"
  source_note: "2026-08 레퍼런스 3개 분석"
"""

from __future__ import annotations

from pathlib import Path

from src.utils.file_utils import read_yaml, write_yaml
from src.utils.time_utils import now_iso

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
STYLE_RULES_PATH = CONFIG_DIR / "style-rules.yaml"


def _deep_merge(base: dict, updates: dict) -> dict:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def update_style_rules(reference_dir: str | Path) -> dict:
    reference_dir = Path(reference_dir)
    style_rules = read_yaml(STYLE_RULES_PATH)

    notes_path = reference_dir / "notes.yaml"
    if notes_path.exists():
        notes = read_yaml(notes_path) or {}
        style_name = notes.pop("style_name", style_rules.get("default_style", "clean_travel"))
        existing = style_rules["styles"].get(style_name, {})
        style_rules["styles"][style_name] = _deep_merge(dict(existing), notes)

        style_rules.setdefault("reference_notes", []).append({
            "applied_at": now_iso(),
            "style_name": style_name,
            "source": str(notes_path),
            "summary": notes.get("source_note", "notes.yaml 기반 규칙 병합"),
        })
        write_yaml(STYLE_RULES_PATH, style_rules)
        return {"status": "merged", "style_name": style_name, "notes_file": str(notes_path)}

    # notes.yaml이 없으면 폴더 안 파일만 기록해두고, 사람이 정리해서 다시 실행하도록 안내
    files = [p.name for p in reference_dir.glob("*") if p.is_file()] if reference_dir.exists() else []
    style_rules.setdefault("reference_notes", []).append({
        "applied_at": now_iso(),
        "style_name": None,
        "source": str(reference_dir),
        "summary": f"notes.yaml이 없어 규칙 병합은 건너뜀. 발견된 파일: {files}",
    })
    write_yaml(STYLE_RULES_PATH, style_rules)
    return {"status": "logged_only", "files": files}
