"""실행 로그 유틸리티.

각 프로젝트의 logs/run-log.md 에 단계별 진행상황/실패 사유를 남긴다.
콘솔에도 동시에 출력해 CLI 사용 시 진행 상황을 바로 볼 수 있게 한다.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path


class RunLogger:
    def __init__(self, log_path: Path, echo: bool = True):
        self.log_path = log_path
        self.echo = echo
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.write_text(
                f"# Run Log\n\n생성 시각: {datetime.now().isoformat(timespec='seconds')}\n\n",
                encoding="utf-8",
            )

    def _write(self, line: str) -> None:
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def step_start(self, step: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"- [{ts}] ▶ **{step}** 시작"
        self._write(line)
        if self.echo:
            print(f"[{ts}] ▶ {step} 시작", file=sys.stderr)

    def step_ok(self, step: str, detail: str = "") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        suffix = f" — {detail}" if detail else ""
        line = f"- [{ts}] ✅ **{step}** 완료{suffix}"
        self._write(line)
        if self.echo:
            print(f"[{ts}] ✅ {step} 완료{suffix}", file=sys.stderr)

    def step_warn(self, step: str, detail: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"- [{ts}] ⚠️ **{step}** 경고 — {detail}"
        self._write(line)
        if self.echo:
            print(f"[{ts}] ⚠️ {step} 경고 — {detail}", file=sys.stderr)

    def step_fail(self, step: str, detail: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"- [{ts}] ❌ **{step}** 실패 — {detail}"
        self._write(line)
        if self.echo:
            print(f"[{ts}] ❌ {step} 실패 — {detail}", file=sys.stderr)

    def info(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._write(f"- [{ts}] ℹ️ {message}")
        if self.echo:
            print(f"[{ts}] ℹ️ {message}", file=sys.stderr)
