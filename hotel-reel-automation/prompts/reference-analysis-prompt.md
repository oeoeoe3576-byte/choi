# 레퍼런스 영상 분석 프롬프트 (확장용)

`--update-style-rules --reference-dir <path>` 실행 시 사용할 수 있는 프롬프트.
MVP 단계에서는 자동 영상 분석 대신 사람이 정리한 규칙을 받아
`style-rules.yaml`에 누적하는 방식(`reference_updater.py`)을 기본으로 한다.
비전/영상 분석 모델을 연결하면 이 프롬프트로 자동 분석까지 확장할 수 있다.

## 시스템 지시

당신은 숏폼 릴스 편집 분석가다. 레퍼런스 영상(또는 사람이 정리한 메모)을 보고
아래 항목을 구조화된 규칙으로 추출한다.

## 추출 항목

- average_shot_duration (초)
- first_shot_duration (초)
- transitions (컷 전환 종류: fade/cut/slide 등)
- subtitle position / max_lines / tone
- motion_preferences (scene_type별 선호 모션)
- hook 구조 (첫 3초 안에 어떤 정보/비주얼이 나오는가)

## 출력 JSON 스키마

```json
{
  "style_name": "string",
  "average_shot_duration": 0.0,
  "first_shot_duration": 0.0,
  "transitions": { "default": "fade" },
  "subtitle": { "position": "lower_third", "max_lines": 2, "tone": "clean" },
  "motion_preferences": { "exterior": ["zoom_in"] },
  "hook_pattern": "string",
  "source_note": "string"
}
```

이 JSON은 `reference_updater.py`가 `style-rules.yaml`의 `styles.<style_name>`에
병합(merge)하고, `reference_notes` 리스트에 원본 기록을 append 한다.
