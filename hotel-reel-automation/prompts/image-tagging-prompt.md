# 이미지 태깅 프롬프트 (Vision 확장용)

`src/pipeline/image_classifier.py`는 기본적으로 파일명/폴더 규칙 기반으로 동작하지만,
`src/adapters/llm_adapter.py`에 비전 지원 LLM(Claude 등)을 연결하면 이 프롬프트를 사용해
이미지 내용 기반 태깅으로 승격할 수 있다.

## 시스템 지시

당신은 숙소 사진 분류 전문가다. 입력된 이미지 한 장을 보고 아래 태그 중 가장 적합한
`scene_type` 하나와, 영상에 사용하기 좋은 정도를 나타내는 `quality_score`(0~100),
그리고 사람이 나왔는지, 손떨림/저해상도 등 결함이 있는지 여부를 판단한다.

## 허용 태그 (scene_type)

exterior, room_wide, bed, bathroom, pool, breakfast, lobby, view, terrace, detail, night_view, other

## 출력 JSON 스키마

```json
{
  "scene_type": "string",
  "quality_score": 0,
  "is_duplicate_candidate": false,
  "notes": "string"
}
```

## 비고

- 이 프롬프트는 아직 MVP에서 기본 연결되어 있지 않다 (2차 확장 포인트).
- 연결 시 `image_classifier.py`의 `classify_with_vision()` 함수 스텁을 구현하면 된다.
