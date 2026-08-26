"""자막 데이터 모델."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SubtitleCue:
    index: int
    start: float          # seconds
    end: float             # seconds
    lines: list[str] = field(default_factory=list)
    emphasis_words: list[str] = field(default_factory=list)
    layout: str = "lower_third"

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "lines": self.lines,
            "text": "\n".join(self.lines),
            "emphasis_words": self.emphasis_words,
            "layout": self.layout,
        }

    def to_srt_block(self) -> str:
        def fmt(t: float) -> str:
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = int(t % 60)
            ms = int(round((t - int(t)) * 1000))
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        text = "\n".join(self.lines)
        return f"{self.index}\n{fmt(self.start)} --> {fmt(self.end)}\n{text}\n"
