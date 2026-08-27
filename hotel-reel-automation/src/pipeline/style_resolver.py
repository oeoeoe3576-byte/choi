"""스타일 프리셋 로딩 공용 헬퍼.

project_loader가 만든 Project(tone/style_preset)를 config/style-rules.yaml의
실제 스타일 딕셔너리로 변환한다. shot_planner(컷 길이/모션)와 script_generator
(컷 수/훅 문구) 양쪽이 "같은 스타일이 결정한 같은 값"을 봐야 하는데, 예전에
자막 강조색 키를 두 군데서 따로 읽다가 어긋난 버그가 실제로 있었다
(config/subtitle-template.yaml의 tone_emphasis_color 관련). 같은 실수를
반복하지 않으려고 스타일 해석 로직은 여기 한 곳에만 둔다.
"""

from __future__ import annotations

from pathlib import Path

from src.models.project import Project
from src.utils.file_utils import read_yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


def load_style(project: Project) -> dict:
    style_rules = read_yaml(CONFIG_DIR / "style-rules.yaml")
    style_name = project.style_preset or style_rules["tone_to_style"].get(
        project.tone, style_rules["default_style"]
    )
    style = style_rules["styles"].get(style_name, style_rules["styles"][style_rules["default_style"]])
    return {"style_name": style_name, **style}
