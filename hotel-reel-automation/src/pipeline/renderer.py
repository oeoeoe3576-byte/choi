"""렌더링 모듈 (FFmpeg 기반).

각 컷을 "이미지 -> 9:16 크롭 -> zoompan 모션 -> (fade 전환) -> (자막 번인)" 순서로
개별 클립으로 만든 뒤, concat demuxer로 이어 붙여 최종 mp4를 만든다.

FFmpeg를 선택한 이유는 README/CLAUDE.md에 설명되어 있음 (환경 의존성이 적고
코드로 완전히 파라미터화할 수 있어 config 파일만 바꾸면 결과가 바뀌기 때문).
"""

from __future__ import annotations

from pathlib import Path

from PIL import ImageFont

from src.models.project import Project
from src.models.shot import Shot
from src.models.subtitle import SubtitleCue
from src.utils.ffmpeg_utils import (
    build_motion_expr,
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
    emphasis_color: str, fade_seconds: float, ass_path: Path | None,
    fontsize: int, font_path: str | None,
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

    if cfg["subtitle_burn_in"]["enabled"] and cue is not None and cue.lines and ass_path is not None:
        write_ass_file(cue, sub_layout, W, H, emphasis_color, ass_path, fontsize, font_path)
        filters.append(f"ass={_escape_filter_path(str(ass_path))}")

    return ",".join(filters)


def _preset_type_for(preset_name: str) -> str:
    mapping = {
        "zoom_in": "zoom", "zoom_out": "zoom",
        "pan_left": "pan", "pan_right": "pan", "pan_up": "pan", "pan_down": "pan",
        "slow_drift": "drift", "slight_parallax": "parallax",
    }
    return mapping.get(preset_name, "zoom")


def _hex_to_ass_color(hex_color: str, opacity: float = 1.0) -> str:
    """'#RRGGBB' + opacity(0=투명,1=불투명) -> ASS의 '&HAABBGGRR' 형식.

    ASS 알파는 반대(0x00=완전 불투명, 0xFF=완전 투명)라서 반전해서 넣는다.
    """
    hex_color = hex_color.lstrip("#")
    rr, gg, bb = hex_color[0:2], hex_color[2:4], hex_color[4:6]
    alpha = max(0, min(255, round((1 - opacity) * 255)))
    return f"&H{alpha:02X}{bb}{gg}{rr}"


def _ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


def _build_ass_line_text(lines: list[str], emphasis_words: list[str], emphasis_color_tag: str,
                          base_color_tag: str) -> str:
    """cue의 여러 줄을 ASS \\N으로 합치고, emphasis_words에 해당하는 부분만
    색을 다르게 감싼다 (한 줄 안에서 처음 등장하는 위치 1곳만 강조)."""
    rendered_lines = []
    for line in lines:
        escaped = _ass_escape(line)
        # 긴 강조어부터 처리해야 짧은 강조어가 긴 강조어의 부분 문자열을 먼저
        # 먹어버리는 것을 방지할 수 있다.
        for word in sorted(set(emphasis_words), key=len, reverse=True):
            if not word or word not in escaped:
                continue
            escaped = escaped.replace(
                word, f"{{\\c{emphasis_color_tag}&}}{word}{{\\c{base_color_tag}&}}", 1,
            )
        rendered_lines.append(escaped)
    return "\\N".join(rendered_lines)


def compute_global_fontsize(layout: dict, video_width: int, video_height: int) -> int:
    """영상 전체에서 공통으로 쓸 자막 폰트 크기를 '한 번만' 계산한다.

    컷마다 그 컷의 실제 텍스트 길이에 맞춰 폰트 크기를 다시 계산하면, 짧은
    문장은 크게/긴 문장은 작게 나와서 컷마다 자막 크기와 박스 크기가
    들쭉날쭉해 보인다. 그래서 스타일에 설정된 max_chars_per_line(글자 수
    예산)을 기준으로 크기를 한 번만 정하고, 영상 전체 컷이 이 크기를
    공유한다 (개별 컷 텍스트가 이 예산을 넘는 예외 상황에서만
    `_fit_fontsize_for_cue`가 해당 컷 한정으로 축소한다).
    """
    margin_side_pct = layout.get("margin_side_pct", 8)
    usable_width = video_width * (1 - 2 * margin_side_pct / 100)
    max_chars = max(layout.get("max_chars_per_line", 16), 6)
    fit_by_width = usable_width / max_chars
    fit_by_height_pct = video_height * layout["font_size_pct"] / 100
    return max(int(min(fit_by_width, fit_by_height_pct)), 24)


def _measure_text_block(lines: list[str], font_path: str | None, fontsize: int) -> tuple[float, float, float]:
    """(가장 긴 줄의 픽셀 폭, 줄 하나의 높이, 전체 텍스트 블록 높이)를 실측한다."""
    if font_path:
        font = ImageFont.truetype(font_path, fontsize)
    else:
        font = ImageFont.load_default()
    widths = [font.getlength(line) for line in lines] or [0.0]
    ascent, descent = font.getmetrics()
    line_height = (ascent + descent) * 1.25  # 자간/줄간 여유
    return max(widths), line_height, line_height * len(lines)


def _fit_fontsize_for_cue(lines: list[str], font_path: str | None, base_fontsize: int,
                           usable_width: float) -> int:
    """이 컷의 텍스트가 (오버플로 병합 등으로) 예산보다 길면, 이 컷만 축소한다.

    대부분의 컷은 base_fontsize를 그대로 반환해 영상 전체 자막 크기가
    일정하게 유지된다.
    """
    if not lines or not font_path:
        return base_fontsize
    max_width, _, _ = _measure_text_block(lines, font_path, base_fontsize)
    if max_width <= usable_width or max_width <= 0:
        return base_fontsize
    scale = usable_width / max_width
    return max(int(base_fontsize * scale * 0.96), 20)


def write_ass_file(cue: SubtitleCue, layout: dict, video_width: int, video_height: int,
                    emphasis_color: str, out_path: Path, base_fontsize: int,
                    font_path: str | None) -> None:
    """libass(ass 필터)로 렌더링할 .ass 자막 파일을 컷(클립) 하나 분량으로 만든다.

    자막 배경 박스는 ASS의 기본 "줄마다 박스"(BorderStyle=3) 대신, 실제 텍스트
    크기를 PIL로 측정해 여러 줄을 감싸는 사각형 하나를 직접 그린다 (Layer 0).
    그 위에 텍스트를 outline만 있는 스타일로 얹는다 (Layer 1). 이렇게 해야
    두 줄 자막에서 줄마다 폭이 다른 박스 두 개가 계단처럼 겹쳐 보이는 문제가
    없다.
    """
    margin_side_pct = layout.get("margin_side_pct", 8)
    usable_width = video_width * (1 - 2 * margin_side_pct / 100)
    fontsize = _fit_fontsize_for_cue(cue.lines, font_path, base_fontsize, usable_width)

    font_family = layout.get("font_family", "NanumGothic").split(",")[0].strip()
    max_line_w, line_height, block_h = _measure_text_block(cue.lines, font_path, fontsize)

    pad_h, pad_v = fontsize * 0.5, fontsize * 0.32
    box_w = max_line_w + 2 * pad_h
    box_h = block_h + 2 * pad_v
    box_left = (video_width - box_w) / 2

    position = layout["position"]
    if position == "lower_third":
        margin_v_px = video_height * layout["margin_bottom_pct"] / 100
        box_top = video_height - margin_v_px - box_h
    elif position == "upper_third":
        margin_v_px = video_height * layout.get("margin_top_pct", 10) / 100
        box_top = margin_v_px
    else:
        box_top = (video_height - box_h) / 2

    text_center_x = video_width / 2
    text_center_y = box_top + box_h / 2

    base_color = _hex_to_ass_color(layout["font_color"], 1.0)
    outline_color = _hex_to_ass_color(layout["stroke_color"], 1.0)
    emphasis_ass_color = _hex_to_ass_color(emphasis_color, 1.0)
    box_enabled = layout.get("box_enabled", False)

    text = _build_ass_line_text(cue.lines, cue.emphasis_words, emphasis_ass_color, base_color)
    end_ts = _ass_timestamp(cue.end - cue.start)

    events = []
    if box_enabled:
        # "&H{AA}{BB}{GG}{RR}" 형식에서 알파 2자리(index 2:4)와 색상 6자리(index 4:10)를
        # 분리해 \1c(색)와 \1a(알파) override 태그에 각각 넣는다.
        box_fill = _hex_to_ass_color(layout["box_color"], layout.get("box_opacity", 0.35))
        box_alpha_hex, box_rgb_hex = box_fill[2:4], box_fill[4:10]
        events.append(
            f"Dialogue: 0,0:00:00.00,{end_ts},Box,,0,0,0,,"
            f"{{\\an7\\pos({box_left:.1f},{box_top:.1f})\\1c&H{box_rgb_hex}&\\1a&H{box_alpha_hex}&\\p1}}"
            f"m 0 0 l {box_w:.0f} 0 l {box_w:.0f} {box_h:.0f} l 0 {box_h:.0f}{{\\p0}}"
        )
    events.append(
        f"Dialogue: 1,0:00:00.00,{end_ts},Text,,0,0,0,,"
        f"{{\\an5\\pos({text_center_x:.1f},{text_center_y:.1f})}}{text}"
    )

    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Text,{font_family},{fontsize},{base_color},&H000000FF,{outline_color},&H00000000,-1,0,0,0,100,100,0,0,1,{max(layout.get('stroke_width_px', 3), 1)},0,5,0,0,0,1
Style: Box,{font_family},{fontsize},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{chr(10).join(events)}
"""
    write_text(out_path, ass_content)


def _ass_timestamp(seconds: float) -> str:
    seconds = max(seconds, 0.1)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def render_project(
    project: Project, shots: list[Shot], cues: list[SubtitleCue], style: dict,
    log_path: Path | None = None,
) -> Path:
    cfg = load_render_config()
    binary = resolve_ffmpeg_binary(cfg.get("ffmpeg_binary", "ffmpeg"))
    # 한글 폰트가 시스템에 하나도 없으면 자막이 빈 사각형(tofu)으로 나올 수 있으니,
    # 그 경우엔 아예 자막 번인을 건너뛴다 (영상 자체는 계속 만들어지게).
    font_path = find_first_existing_font(cfg["subtitle_burn_in"]["font_path_candidates"])
    has_korean_font = font_path is not None

    sub_style = style.get("subtitle", {})
    from src.pipeline.subtitle_generator import load_subtitle_config
    sub_cfg = load_subtitle_config()
    layout_key = sub_style.get("position", "lower_third")
    layout = dict(sub_cfg["layouts"].get(layout_key, sub_cfg["layouts"]["lower_third"]))
    if "max_lines" in sub_style:
        layout["max_lines"] = sub_style["max_lines"]

    # 강조 색상은 자막 "위치" 템플릿(layout, subtitle-template.yaml)이 아니라
    # 스타일 프리셋의 subtitle.tone(clean/bold/friendly, style-rules.yaml)에서 가져와야 한다.
    # layout 쪽에는애초에 tone 키가 없어서, layout.get("tone", ...)로 읽으면 항상
    # 기본값(clean=노랑)으로 고정되는 버그가 있었다.
    tone_key = sub_style.get("tone", "clean")
    emphasis_color = sub_cfg.get("tone_emphasis_color", {}).get(tone_key, "#FFD84D")

    fade_seconds = style.get("transitions", {}).get("duration", 0.3)
    subtitle_enabled = cfg["subtitle_burn_in"]["enabled"] and has_korean_font

    # 영상 전체가 공유할 폰트 크기를 여기서 딱 한 번만 계산한다 (컷마다 다시
    # 계산하면 자막 크기가 컷마다 들쭉날쭉해진다 - _build_shot_filter 안의
    # write_ass_file()이 컷별로 예외적으로만 이 값보다 축소한다).
    global_fontsize = compute_global_fontsize(layout, cfg["output"]["width"], cfg["output"]["height"])

    clips_dir = ensure_dir(project.output_dir / "_clips")
    cue_by_index = {c.index: c for c in cues}

    clip_paths: list[Path] = []
    for shot in shots:
        image_path = project.project_dir / shot.image
        if not image_path.exists():
            raise FileNotFoundError(f"컷 {shot.shot_index}의 이미지가 없습니다: {image_path}")

        ass_path = clips_dir / f"shot_{shot.shot_index:02d}.ass" if subtitle_enabled else None
        cfg_for_shot = dict(cfg)
        cfg_for_shot["subtitle_burn_in"] = {**cfg["subtitle_burn_in"], "enabled": subtitle_enabled}
        filter_str = _build_shot_filter(
            shot, cue_by_index.get(shot.shot_index), cfg_for_shot, layout, emphasis_color,
            fade_seconds, ass_path, global_fontsize, font_path,
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
        for p in clips_dir.glob("*.ass"):
            p.unlink(missing_ok=True)
        concat_list.unlink(missing_ok=True)
        try:
            clips_dir.rmdir()
        except OSError:
            pass

    return output_path
