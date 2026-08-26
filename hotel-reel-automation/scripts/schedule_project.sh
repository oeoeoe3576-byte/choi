#!/usr/bin/env bash
# 프로젝트 렌더링을 예약하고, 필요하면 cron에 주기 실행 작업을 등록한다.
#
# 사용법:
#   scripts/schedule_project.sh <프로젝트 경로> "<YYYY-MM-DD HH:MM>" [--install-cron]
#
# 예:
#   scripts/schedule_project.sh ./sample_projects/sample_hotel "2026-08-28 09:00"
#   scripts/schedule_project.sh ./sample_projects/sample_hotel "2026-08-28 09:00" --install-cron
#
# --install-cron 을 주면, "5분마다 --run-due 실행" cron 작업을 등록한다
# (macOS/Linux 공통. macOS는 cron에 터미널/디스크 접근 권한을 따로 허용해야 할 수 있다).
# 이미 동일한 cron 라인이 있으면 중복 등록하지 않는다.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT_DIR="$(pwd)"

if [ "$#" -lt 2 ]; then
  echo "사용법: $0 <프로젝트 경로> \"<YYYY-MM-DD HH:MM>\" [--install-cron]" >&2
  exit 1
fi

PROJECT_DIR="$1"
SCHEDULE_AT="$2"
INSTALL_CRON="${3:-}"

python3 -m src.main --project "$PROJECT_DIR" --schedule "$SCHEDULE_AT"

if [ "$INSTALL_CRON" = "--install-cron" ]; then
  CRON_CMD="cd $ROOT_DIR && /usr/bin/env python3 -m src.main --run-due >> $ROOT_DIR/logs/cron-run-due.log 2>&1"
  CRON_LINE="*/5 * * * * $CRON_CMD"
  mkdir -p "$ROOT_DIR/logs"

  EXISTING_CRON="$(crontab -l 2>/dev/null || true)"
  if echo "$EXISTING_CRON" | grep -qF -- "$CRON_CMD"; then
    echo "cron 작업이 이미 등록되어 있습니다."
  else
    { echo "$EXISTING_CRON"; echo "$CRON_LINE"; } | crontab -
    echo "cron에 5분마다 '--run-due' 실행 작업을 등록했습니다."
  fi
fi

echo ""
echo "예약 목록 확인: python -m src.main --list-schedules"
echo "예약 취소:      python -m src.main --cancel-schedule <job_id>"
