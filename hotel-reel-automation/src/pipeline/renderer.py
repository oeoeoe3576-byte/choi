"""렌더링 모듈 (FFmpeg 기반).

각 컷을 "이미지 -> 9:16 크롭 -> zoompan 모션 -> (fade 전환) -> (자막 번인)" 순서로
개별 클립으로 만든 뒤, concat demuxer로 이어 붙여 최종 mp4를 만든다.

FFmpeg를 선택한 이유는 README/CLAUDE.md에 설명되어 있음 (환경 의존성이 적고
코드로 완전히 파라미터화할 수 있어 config 파일만 바꾸면 결과가 바뀌기 때문).
"""

from __future__ import annotations

from pathlib import Path

from src.models.project import Project
from src.models.shot import Shot
from src.models.subtitle import SubtitleCue
from src.utils.ffmpeg_utils import (
    build_motion_expr,
    escape_drawtext_text,
    find_first_existing_font,
    resolve_ffmpeg_binary,
    run_ffmpeg,
)
from src.utils.file_utils import ensure_dir, read_yaml, write_text

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


def load_render_config() -> dict:
    return read_yaml(CONFIG_DIR / "render-config.yaml")


def _escape_filter_path(path: str) -> str:
    # ffmpeg 필터 옵션 값에서 콜론/백슬래시는 이스케이프 필요
    return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’")


def _build_shot_filter(
    shot: Shot, cue: SubtitleCue | None, cfg: dict, sub_layout: dict,
    font_path: str | None, fade_seconds: float,
) -> str:
    W, H = cfg["output"]["width"], cfg["output"]["height"]
    fps = cfg["output"]["fps"]
    frames = max(int(round(shot.duration * fps)), 1)

    motion = build_motion_expr(
        preset_type=_preset_type_for(shot.motion.preset),
        direction=shot.motion.direction,
        start_scale=shot.motion.start_scale,
        end_scale=shot.motion.end_scale,
        travel_pct=shot.motion.travel_pct,
        max_frame_idx=frames - 1,
    )

    filters = [
        f"scale={W}:{H}:force_original_aspect_ratio=increase",
        f"crop={W}:{H}",
        f"scale={W*2}:{H*2}",
        f"zoompan=z='{motion.zoom_expr}':x='{motion.x_expr}':y='{motion.y_expr}':d={frames}:s={W}x{H}:fps={fps}",
        "format=yuv420p",
    ]

    fd = min(fade_seconds, max(shot.duration * 0.4, 0.05))
    if shot.transition_in == "fade":
        filters.append(f"fade=t=in:st=0:d={fd:.3f}")
    if shot.transition_out == "fade":
        out_start = max(shot.duration - fd, 0.0)
        filters.append(f"fade=t=out:st={out_start:.3f}:d={fd:.3f}")

    if cfg["subtitle_burn_in"]["enabled"] and cue is not None and cue.lines and font_path:
        filters.append(_drawtext_filter(cue, sub_layout, font_path, W, H))

    return ",".join(filters)


def _preset_type_for(preset_name: str) -> str:
    mapping = {
        "zoom_in": "zoom", "zoom_out": "zoom",
        "pan_left": "pan", "pan_right": "pan", "pan_up": "pan", "pan_down": "pan",
        "slow_drift": "drift", "slight_parallax": "parallax",
    }
    return mapping.get(preset_name, "zoom")


def _drawtext_filter(
    cue: SubtitleCue, layout: dict, font_path: str, video_width: int, video_height: int,
) -> str:
    text = "\n".join(cue.lines)
    escaped_text = escape_drawtext_text(text)

    # 한글은 대체로 정사각형에 가까운 전각 글자이므로, 폰트 크기를 '영상 높이의 %'로만 정하면
    # 글자 수가 많은 줄에서 영상 폭(1080px)을 넘어가 잘리는 문제가 생긴다.
    # 그래서 (1) 높이 기준 최대 크기와 (2) 이 컷의 실제 줄 길이가 폭 안에 들어오는 크기
    # 중 더 작은 값을 사용해 항상 화면 안에 들어오도록 한다.
    margin_side_pct = layout.get("margin_side_pct", 8)
    usable_width = video_width * (1 - 2 * margin_side_pct / 100)
    longest_line_chars = max((len(line) for line in cue.lines), default=layout["max_chars_per_line"])
    longest_line_chars = max(longest_line_chars, 6)
    fit_by_width = usable_width / longest_line_chars
    fit_by_height_pct = video_height * layout["font_size_pct"] / 100
    fontsize = max(int(min(fit_by_width, fit_by_height_pct)), 24)
    line_spacing = layout.get("line_spacing_px", 8)

    position = layout["position"]
    if position == "lower_third":
        y_expr = f"h-(h*{layout['margin_bottom_pct']}/100)-text_h"
    elif position == "upper_third":
        y_expr = f"h*{layout.get('margin_top_pct', 10)}/100"
    else:
        y_expr = "(h-text_h)/2"

    box_part = ""
    if layout.get("box_enabled"):
        box_color = layout["box_color"].lstrip("#")
        box_part = f":box=1:boxcolor=0x{box_color}@{layout['box_opacity']}:boxborderw=20"

    font_color = layout["font_color"].lstrip("#")
    stroke_color = layout["stroke_color"].lstrip("#")

    return (
        f"drawtext=text='{escaped_text}':fontfile='{_escape_filter_path(font_path)}'"
        f":fontsize={fontsize}:fontcolor=0x{font_color}:bordercolor=0x{stroke_color}"
        f":borderw={layout['stroke_width_px']}:line_spacing={line_spacing}"
        f"{box_part}:x=(w-text_w)/2:y={y_expr}"
    )


def render_project(
    project: Project, shots: list[Shot], cues: list[SubtitleCue], style: dict,
    log_path: Path | None = None,
) -> Path:
    cfg = load_render_config()
    binary = resolve_ffmpeg_binary(cfg.get("ffmpeg_binary", "ffmpeg"))
    font_path = find_first_existing_font(cfg["subtitle_burn_in"]["font_path_candidates"])

    sub_style = style.get("subtitle", {})
    from src.pipeline.subtitle_generator import load_subtitle_config
    sub_cfg = load_subtitle_config()
    layout_key = sub_style.get("position", "lower_third")
    layout = dict(sub_cfg["layouts"].get(layout_key, sub_cfg["layouts"]["lower_third"]))
    if "max_lines" in sub_style:
        layout["max_lines"] = sub_style["max_lines"]

    fade_seconds = style.get("transitions", {}).get("duration", 0.3)

    clips_dir = ensure_dir(project.output_dir / "_clips")
    cue_by_index = {c.index: c for c in cues}

    clip_paths: list[Path] = []
    for shot in shots:
        image_path = project.project_dir / shot.image
        if not image_path.exists():
            raise FileNotFoundError(f"컷 {shot.shot_index}의 이미지가 없습니다: {image_path}")

        filter_str = _build_shot_filter(
            shot, cue_by_index.get(shot.shot_index), cfg, layout, font_path, fade_seconds,
        )
        clip_path = clips_dir / f"shot_{shot.shot_index:02d}.mp4"
        run_ffmpeg(
            binary,
            [
                "-loop", "1", "-i", str(image_path),
                "-vf", filter_str,
                "-t", f"{shot.duration:.3f}",
                "-r", str(cfg["output"]["fps"]),
                "-pix_fmt", cfg["output"]["pixel_format"],
                "-c:v", cfg["output"]["video_codec"],
                "-crf", str(cfg["output"]["crf"]),
                "-preset", cfg["output"]["preset"],
                str(clip_path),
            ],
            log_path=log_path,
        )
        clip_paths.append(clip_path)

    concat_list = clips_dir / "concat_list.txt"
    write_text(
        concat_list,
        "\n".join(f"file '{p.resolve()}'" for p in clip_paths) + "\n",
    )

    output_path = project.output_dir / cfg["output"]["filename"]
    concat_args = [
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c:v", "copy", "-an", str(output_path),
    ]
    run_ffmpeg(binary, concat_args, log_path=log_path)

    bgm_cfg = cfg.get("bgm", {})
    bgm_path = project.project_dir / "audio" / "bgm.mp3"
    if bgm_cfg.get("enabled") and bgm_path.exists():
        with_audio = project.output_dir / f"_with_audio_{cfg['output']['filename']}"
        run_ffmpeg(
            binary,
            [
                "-i", str(output_path), "-stream_loop", "-1", "-i", str(bgm_path),
                "-filter_complex",
                f"[1:a]volume={bgm_cfg.get('volume', 0.6)},"
                f"afade=t=out:st={max(project.video_length - bgm_cfg.get('fade_out_seconds', 1.0), 0)}"
                f":d={bgm_cfg.get('fade_out_seconds', 1.0)}[a]",
                "-map", "0:v", "-map", "[a]",
                "-c:v", "copy", "-c:a", cfg["output"]["audio_codec"],
                "-b:a", cfg["output"]["audio_bitrate"],
                "-shortest", str(with_audio),
            ],
            log_path=log_path,
        )
        with_audio.replace(output_path)

    if not cfg["logging"].get("keep_intermediate_files", False):
        for p in clip_paths:
            p.unlink(missing_ok=True)
        concat_list.unlink(missing_ok=True)
        try:
            clips_dir.rmdir()
        except OSError:
            pass

    return output_path
