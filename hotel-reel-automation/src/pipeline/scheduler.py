"""예약 실행(Scheduler) 모듈.

상시 데몬 없이 동작하는 것을 전제로 한다:
  1. --schedule 으로 등록하면 scheduled-jobs.json에 기록된다.
  2. 등록 시점에 이미 예약 시각이 지났다면 즉시 실행한다.
  3. 미래 시각이면, cron/at 등 OS 스케줄러가 주기적으로
     `python -m src.main --run-due` 를 호출하도록 설정하는 것을 권장한다
     (scripts/schedule_project.sh 참고).

CLI:
  --schedule "YYYY-MM-DD HH:MM"
  --list-schedules
  --cancel-schedule job_001
  --run-due
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from src.models.render_job import RenderJob
from src.utils.file_utils import read_json, write_json
from src.utils.time_utils import now_iso, parse_schedule_datetime

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def _jobs_file() -> Path:
    return ROOT_DIR / "scheduled-jobs.json"


def _load_jobs() -> list[dict]:
    path = _jobs_file()
    if not path.exists():
        return []
    return read_json(path)


def _save_jobs(jobs: list[dict]) -> None:
    write_json(_jobs_file(), jobs)


def add_job(project_dir: str, scheduled_at: str, tone_override: str | None = None,
            length_override: int | None = None) -> RenderJob:
    scheduled_dt = parse_schedule_datetime(scheduled_at)
    job = RenderJob(
        job_id=f"job_{uuid.uuid4().hex[:8]}",
        project_dir=str(Path(project_dir).resolve()),
        scheduled_at=scheduled_dt.isoformat(timespec="minutes"),
        created_at=now_iso(),
        tone_override=tone_override,
        length_override=length_override,
    )
    jobs = _load_jobs()
    jobs.append(job.to_dict())
    _save_jobs(jobs)
    return job


def list_jobs() -> list[dict]:
    return _load_jobs()


def cancel_job(job_id: str) -> bool:
    jobs = _load_jobs()
    found = False
    for job in jobs:
        if job["job_id"] == job_id and job["status"] == "pending":
            job["status"] = "cancelled"
            found = True
    _save_jobs(jobs)
    return found


def due_jobs(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    result = []
    for job in _load_jobs():
        rj = RenderJob(**job)
        if rj.is_due(now):
            result.append(job)
    return result


def mark_job(job_id: str, status: str, error: str | None = None) -> None:
    jobs = _load_jobs()
    for job in jobs:
        if job["job_id"] == job_id:
            job["status"] = status
            job["last_error"] = error
            job["finished_at"] = now_iso()
    _save_jobs(jobs)


def run_due(runner) -> list[dict]:
    """runner(project_dir, tone_override, length_override) -> None 형태의 콜백을 실행."""
    results = []
    for job in due_jobs():
        job_id = job["job_id"]
        jobs = _load_jobs()
        for j in jobs:
            if j["job_id"] == job_id:
                j["status"] = "running"
        _save_jobs(jobs)
        try:
            runner(job["project_dir"], job.get("tone_override"), job.get("length_override"))
            mark_job(job_id, "done")
            results.append({"job_id": job_id, "status": "done"})
        except Exception as exc:  # noqa: BLE001
            mark_job(job_id, "failed", error=str(exc))
            results.append({"job_id": job_id, "status": "failed", "error": str(exc)})
    return results
