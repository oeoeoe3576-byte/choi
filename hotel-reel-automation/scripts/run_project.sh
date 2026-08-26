#!/usr/bin/env bash
# 프로젝트 폴더 하나를 바로 렌더링한다.
#
# 사용법:
#   scripts/run_project.sh <프로젝트 경로> [--tone emotional] [--length 20] [--skip-render]
#
# 예:
#   scripts/run_project.sh ./sample_projects/sample_hotel
#   scripts/run_project.sh ./sample_projects/sample_hotel --tone review --length 15

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ "$#" -lt 1 ]; then
  echo "사용법: $0 <프로젝트 경로> [추가 옵션...]" >&2
  exit 1
fi

PROJECT_DIR="$1"
shift

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

python3 -m src.main --project "$PROJECT_DIR" "$@"
