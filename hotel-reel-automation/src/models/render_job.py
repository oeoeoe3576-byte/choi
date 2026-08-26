"""예약 렌더링 작업(Job) 데이터 모델."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class RenderJob:
    job_id: str
    project_dir: str
    scheduled_at: str          # ISO 8601
    created_at: str
    status: str = "pending"    # pending | running | done | failed | cancelled
    tone_override: str | None = None
    length_override: int | None = None
    last_error: str | None = None
    finished_at: str | None = None

    def is_due(self, now: datetime | None = None) -> bool:
        now = now or datetime.now()
        try:
            scheduled = datetime.fromisoformat(self.scheduled_at)
        except ValueError:
            return False
        return self.status == "pending" and now >= scheduled

    def to_dict(self) -> dict:
        return asdict(self)
