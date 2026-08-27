"""자막 데이터 모델."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SubtitleCue:
    index: int              # 영상 전체 기준 순번 (subtitles.json / .srt용)
    shot_index: int          # 이 자막이 속한 컷(Shot) 번호. 한 컷 안에 여러 개의
                              # 짧은 SubtitleCue가 순차적으로 나올 수 있다.
    start: float             # 영상 전체 기준 시작 시각 (seconds)
    end: float                # 영상 전체 기준 종료 시각 (seconds)
    local_start: float = 0.0  # 이 컷(클립) 자체의 로컬 타임라인 기준 시작 시각
    local_end: float = 0.0    # 이 컷(클립) 자체의 로컬 타임라인 기준 종료 시각
    lines: list[str] = field(default_factory=list)  # 항상 길이 1 (한 줄 고정)
    emphasis_words: list[str] = field(default_factory=list)
    layout: str = "lower_third"

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "shot_index": self.shot_index,
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
