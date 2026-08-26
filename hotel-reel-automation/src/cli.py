"""CLI 인자 파싱 및 명령 디스패치."""

from __future__ import annotations

import argparse
import json
import sys

from src.pipeline import orchestrator, reference_updater, scheduler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description="숙소 사진 기반 숏폼 릴스 자동 제작 파이프라인",
    )
    parser.add_argument("--project", help="프로젝트 폴더 경로 (예: ./sample_projects/sample_hotel)")
    parser.add_argument("--tone", choices=["emotional", "informative", "review", "ad"],
                         help="톤 오버라이드")
    parser.add_argument("--length", type=int, choices=[15, 20, 30], help="영상 길이(초) 오버라이드")
    parser.add_argument("--schedule", help="예약 실행 시각 'YYYY-MM-DD HH:MM'")
    parser.add_argument("--list-schedules", action="store_true", help="예약 목록 확인")
    parser.add_argument("--cancel-schedule", metavar="JOB_ID", help="예약 취소")
    parser.add_argument("--run-due", action="store_true",
                         help="실행 시각이 지난 예약 작업을 모두 렌더링 (cron 등에서 주기 호출)")
    parser.add_argument("--update-style-rules", action="store_true",
                         help="레퍼런스 폴더 기반으로 style-rules.yaml 갱신")
    parser.add_argument("--reference-dir", help="--update-style-rules와 함께 사용")
    parser.add_argument("--skip-render", action="store_true",
                         help="렌더링(ffmpeg) 단계를 건너뛰고 구조/데이터만 생성 (mock 테스트용)")
    parser.add_argument("--image-to-video", action="store_true",
                         help="특정 컷에 AI image-to-video 적용 여부 판단을 활성화 (MVP 스텁)")
    return parser


def _run_project(args) -> int:
    try:
        result = orchestrator.run_pipeline(
            args.project,
            tone=args.tone,
            length=args.length,
            skip_render=args.skip_render,
            image_to_video_enabled=args.image_to_video,
        )
    except orchestrator.PipelineError as exc:
        # 원시 traceback 대신, 어떤 단계에서 왜 실패했는지 바로 알 수 있는 형태로 출력한다.
        print(json.dumps({
            "project": args.project,
            "failed_step": exc.step,
            "error": str(exc.original),
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(json.dumps({"project": args.project, "error": str(exc)}, ensure_ascii=False, indent=2),
              file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(v == "ok" for v in result["steps"].values()) else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.update_style_rules:
        if not args.reference_dir:
            parser.error("--update-style-rules 사용 시 --reference-dir 도 지정해야 합니다.")
        result = reference_updater.update_style_rules(args.reference_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.list_schedules:
        jobs = scheduler.list_jobs()
        print(json.dumps(jobs, ensure_ascii=False, indent=2))
        return 0

    if args.cancel_schedule:
        ok = scheduler.cancel_job(args.cancel_schedule)
        print(json.dumps({"job_id": args.cancel_schedule, "cancelled": ok}, ensure_ascii=False))
        return 0 if ok else 1

    if args.run_due:
        def runner(project_dir, tone_override, length_override):
            orchestrator.run_pipeline(project_dir, tone=tone_override, length=length_override)

        results = scheduler.run_due(runner)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    if not args.project:
        parser.error("--project 경로가 필요합니다. (또는 --list-schedules / --update-style-rules 등을 사용하세요)")

    if args.schedule:
        job = scheduler.add_job(
            args.project, args.schedule, tone_override=args.tone, length_override=args.length,
        )
        from datetime import datetime
        from src.utils.time_utils import parse_schedule_datetime

        if parse_schedule_datetime(args.schedule) <= datetime.now():
            print(f"예약 시각이 이미 지나 즉시 실행합니다: {job.job_id}")
            try:
                rc = _run_project(args)
                scheduler.mark_job(job.job_id, "done" if rc == 0 else "failed")
            except Exception as exc:  # noqa: BLE001
                scheduler.mark_job(job.job_id, "failed", error=str(exc))
                raise
            return rc

        print(json.dumps(job.to_dict(), ensure_ascii=False, indent=2))
        print(
            "예약이 등록되었습니다. 실제 실행 시각에 렌더링되게 하려면 "
            "scripts/schedule_project.sh 를 참고해 cron/at 에 "
            "'python -m src.main --run-due' 를 등록하세요."
        )
        return 0

    return _run_project(args)


if __name__ == "__main__":
    sys.exit(main())
