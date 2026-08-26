#!/usr/bin/env bash
# 레퍼런스 폴더(notes.yaml 포함)를 기반으로 config/style-rules.yaml을 갱신한다.
#
# 사용법:
#   scripts/update_style_rules.sh <레퍼런스 폴더 경로>
#
# 예:
#   scripts/update_style_rules.sh ./sample_projects/sample_hotel/references
#
# notes.yaml 작성법은 prompts/reference-analysis-prompt.md 참고.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ "$#" -lt 1 ]; then
  echo "사용법: $0 <레퍼런스 폴더 경로>" >&2
  exit 1
fi

python3 -m src.main --update-style-rules --reference-dir "$1"
