"""파이프라인 오케스트레이터.

project_loader -> image_classifier -> script_generator -> shot_planner ->
motion_planner -> subtitle_generator -> renderer -> thumbnail_generator ->
caption_generator 순서로 각 단계를 실행하고, 각 단계의 성공/실패를
logs/run-log.md 에 기록한다. 한 단계가 실패해도 어디서 실패했는지 명확히
남기는 것을 원칙으로 한다.
"""

from __future__ import annotations

from pathlib import Path

from src.models.project import Project
from src.pipeline import (
    caption_generator,
    image_classifier,
    motion_planner,
    project_loader,
    script_generator,
    shot_planner,
    subtitle_generator,
)
from src.utils.file_utils import read_json, write_json
from src.utils.logger import RunLogger


class PipelineError(RuntimeError):
    def __init__(self, step: str, original: Exception):
        super().__init__(f"[{step}] {original}")
        self.step = step
        self.original = original


def _load_existing_script(project: Project) -> dict:
    """--reuse-script: 이미 만들어진 script.json을 그대로 쓴다 (재생성 안 함).

    사람이 먼저 script.md/script.json을 보고 확인(또는 직접 수정)한 뒤,
    그 승인된 버전 그대로 렌더링하고 싶을 때 쓴다. LLM 모드에서는 재생성할
    때마다 문구가 조금씩 달라질 수 있어, "확인한 그대로" 렌더링하려면
    재생성 대신 이 경로를 써야 한다.
    """
    script_path = project.project_dir / "script.json"
    if not script_path.exists():
        raise FileNotFoundError(
            f"--reuse-script 옵션을 썼지만 {script_path} 가 없습니다. "
            "먼저 --skip-render로 대본부터 생성한 뒤 확인/수정하고 다시 실행하세요."
        )
    data = read_json(script_path)
    missing = [k for k in ("hook", "scenes", "closing", "cta") if k not in data]
    if missing:
        raise ValueError(f"script.json에 필수 필드가 없습니다: {missing}")
    return {"hook": data["hook"], "scenes": data["scenes"], "closing": data["closing"], "cta": data["cta"]}


def run_pipeline(
    project_dir: str, tone: str | None = None, length: int | None = None,
    skip_render: bool = False, image_to_video_enabled: bool = False,
    reuse_script: bool = False,
) -> dict:
    project = project_loader.load_project(project_dir)
    project = project_loader.apply_overrides(project, tone=tone, length=length)

    logger = RunLogger(project.logs_dir / "run-log.md")
    logger.info(f"프로젝트 로드: {project.project_name} ({project.hotel_name})")
    for w in project.warnings:
        logger.step_warn("project_loader", w)

    result: dict = {"project": project.project_name, "steps": {}}

    if not project.images:
        # 이미지가 0장이면 뒤 단계(특히 렌더링)를 다 돌고 나서야 ffmpeg concat이
        # "No files to concat" 같은 알아보기 힘든 오류로 죽는다. 여기서 바로,
        # 명확한 메시지로 실패시킨다.
        msg = (
            f"{project.images_dir} 에 이미지가 없습니다. 최소 1장 이상 필요합니다. "
            "실제 사진이 없다면 'python3 scripts/generate_mock_images.py "
            f"--project {project.project_dir}' 로 mock 이미지를 먼저 생성하세요."
        )
        logger.step_fail("project_loader", msg)
        raise PipelineError("project_loader", RuntimeError(msg))

    def step(name, fn):
        logger.step_start(name)
        try:
            output = fn()
            logger.step_ok(name)
            result["steps"][name] = "ok"
            return output
        except Exception as exc:  # noqa: BLE001
            logger.step_fail(name, str(exc))
            result["steps"][name] = f"failed: {exc}"
            raise PipelineError(name, exc) from exc

    image_analysis = step(
        "image_classifier",
        lambda: image_classifier.classify_images(project.images, project.project_dir),
    )
    write_json(project.project_dir / "image-analysis.json", image_analysis)

    if reuse_script:
        script = step("script_generator", lambda: _load_existing_script(project))
        # script.md도 재생성된 것처럼 맞춰준다 (일관성 유지, 실제 캡션/렌더는
        # 이미 로드한 script 그대로 사용하므로 대본 내용 자체는 안 바뀐다).
        from src.pipeline.script_generator import render_script_md
        from src.utils.file_utils import write_text
        write_text(project.project_dir / "script.md", render_script_md(project, script, "reused"))
    else:
        script = step("script_generator", lambda: script_generator.run(project))

    shots, style = step(
        "shot_planner", lambda: shot_planner.plan_shots(project, script, image_analysis)
    )

    motion_records = step(
        "motion_planner",
        lambda: motion_planner.assign_motions(shots, style, image_to_video_enabled),
    )
    motion_planner.write_motion_plan(project, motion_records)
    # 최종 edit-plan.json은 모션까지 반영된 shots로 저장
    shot_planner.write_edit_plan(project, shots)

    cues = step(
        "subtitle_generator",
        lambda: subtitle_generator.generate_subtitles(project, shots, style),
    )
    subtitle_generator.write_subtitle_files(project, cues)

    caption_text = step("caption_generator", lambda: caption_generator.run(project, script))

    output_video = None
    if not skip_render:
        def _render():
            from src.pipeline import renderer
            return renderer.render_project(
                project, shots, cues, style, log_path=project.logs_dir / "ffmpeg.log"
            )

        output_video = step("renderer", _render)

        def _thumbnail():
            from src.pipeline import thumbnail_generator
            return thumbnail_generator.generate_thumbnail(project, shots, script["hook"])

        step("thumbnail_generator", _thumbnail)
    else:
        logger.info("skip_render=True: 렌더링 단계를 건너뜁니다 (구조 테스트 모드)")

    logger.info("파이프라인 완료")
    result["output_video"] = str(output_video) if output_video else None
    result["warnings"] = project.warnings
    return result
