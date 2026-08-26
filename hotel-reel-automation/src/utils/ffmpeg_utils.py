"""FFmpeg 명령/필터 구성 유틸리티.

렌더링 엔진으로 FFmpeg를 선택한 이유(설계 원칙 참고):
  - 환경 의존성이 적다 (CapCut 등 GUI 자동화보다 헤드리스 서버에서 안정적으로 동작)
  - 코드 기반이라 파라미터화하기 쉽고, config 파일만 바꾸면 결과가 바뀐다
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class FFmpegNotFoundError(RuntimeError):
    pass


def resolve_ffmpeg_binary(configured: str = "ffmpeg") -> str:
    path = shutil.which(configured) or (configured if Path(configured).exists() else None)
    if not path:
        raise FFmpegNotFoundError(
            f"ffmpeg 실행 파일을 찾을 수 없습니다 ('{configured}'). "
            "설치 후 config/render-config.yaml의 ffmpeg_binary 값을 확인하세요."
        )
    return path


def run_ffmpeg(binary: str, args: list[str], log_path: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [binary, "-y", "-hide_banner", "-loglevel", "error"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if log_path:
        with log_path.open("a", encoding="utf-8") as f:
            f.write("\n$ " + " ".join(cmd) + "\n")
            if result.stdout:
                f.write(result.stdout + "\n")
            if result.stderr:
                f.write(result.stderr + "\n")
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg 실행 실패 (exit={result.returncode})\ncmd: {' '.join(cmd)}\n"
            f"stderr:\n{result.stderr[-4000:]}"
        )
    return result


def find_first_existing_font(candidates: list[str]) -> str | None:
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def escape_drawtext_text(text: str) -> str:
    """ffmpeg drawtext 필터용 텍스트 이스케이프."""
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "’")   # 작은따옴표는 필터 문법과 충돌 -> 유사문자로 치환
    text = text.replace("%", "\\%")
    text = text.replace(",", "\\,")
    text = text.replace("[", "\\[").replace("]", "\\]")
    return text


@dataclass
class MotionExpr:
    """zoompan 필터에 들어갈 z/x/y 표현식 묶음."""
    zoom_expr: str
    x_expr: str
    y_expr: str


def build_motion_expr(preset_type: str, direction: str, start_scale: float,
                       end_scale: float, travel_pct: float, max_frame_idx: int) -> MotionExpr:
    """모션 프리셋 타입에 따라 zoompan z/x/y 표현식을 만든다.

    좌표계: zoompan은 (업스케일된) 입력 프레임 내에서 zoom 배율의 크롭창을 이동시킨다.
    x/y 표현식의 'iw','ih'는 입력 프레임 크기, 'zoom'은 현재 z 표현식의 값.
    """
    idx = max(max_frame_idx, 1)

    if preset_type == "zoom":
        z = f"{start_scale}+({end_scale}-{start_scale})*on/{idx}"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
        return MotionExpr(z, x, y)

    if preset_type == "pan":
        scale = max(start_scale, end_scale, 1.05)
        z = f"{scale}"
        travel = f"(iw-iw/zoom)*{travel_pct / 100.0}"
        if direction == "left":
            x = f"(iw/2-(iw/zoom/2))+({travel})*(0.5-on/{idx})"
            y = "ih/2-(ih/zoom/2)"
        elif direction == "right":
            x = f"(iw/2-(iw/zoom/2))-({travel})*(0.5-on/{idx})"
            y = "ih/2-(ih/zoom/2)"
        elif direction == "up":
            travel_y = f"(ih-ih/zoom)*{travel_pct / 100.0}"
            x = "iw/2-(iw/zoom/2)"
            y = f"(ih/2-(ih/zoom/2))+({travel_y})*(0.5-on/{idx})"
        else:  # down
            travel_y = f"(ih-ih/zoom)*{travel_pct / 100.0}"
            x = "iw/2-(iw/zoom/2)"
            y = f"(ih/2-(ih/zoom/2))-({travel_y})*(0.5-on/{idx})"
        return MotionExpr(z, x, y)

    if preset_type in ("drift", "parallax"):
        z = f"{start_scale}+({end_scale}-{start_scale})*on/{idx}" if end_scale != start_scale else f"{start_scale}"
        travel_x = f"(iw-iw/zoom)*{travel_pct / 100.0}"
        travel_y = f"(ih-ih/zoom)*{travel_pct / 100.0}"
        sign = -1 if preset_type == "parallax" or direction == "diagonal_reverse" else 1
        x = f"(iw/2-(iw/zoom/2))+({sign})*({travel_x})*(0.5-on/{idx})"
        y = f"(ih/2-(ih/zoom/2))+({sign})*({travel_y})*(0.5-on/{idx})"
        return MotionExpr(z, x, y)

    # fallback: 정적 줌인
    z = f"1.0+0.08*on/{idx}"
    return MotionExpr(z, "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)")
