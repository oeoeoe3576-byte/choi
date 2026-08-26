# CLAUDE.md — hotel-reel-automation

이 파일은 Claude Code가 `hotel-reel-automation/` 안에서 작업할 때 참고하는 가이드다.
사람이 "숙소 폴더로 릴스 만들어줘" 같은 요청을 하면, 아래 절차를 따른다.
전체 사용 흐름은 `skills/hotel-reel-skill.md`에 더 자세히 정리돼 있다.

## 이 프로젝트가 하는 일

숙소 사진 폴더 + `input.md`(숙소 정보)를 입력받아, 9:16 숏폼 릴스 제작에 필요한
전 과정(대본 → 컷 편집 계획 → 모션 → 자막 → mp4 렌더링 → 썸네일 → 인스타 캡션)을
자동으로 처리하는 Python CLI 파이프라인이다. 웹서비스가 아니라 Claude Code /
터미널에서 바로 실행하는 재사용형 워크플로우로 설계됐다.

## 빠른 실행

```bash
cd hotel-reel-automation
pip install -r requirements.txt   # 최초 1회
python -m src.main --project ./sample_projects/sample_hotel
```

반드시 `hotel-reel-automation/`을 작업 디렉터리로 두고 `python -m src.main`
형태로 실행해야 한다 (`src` 패키지 상대 import를 쓰기 때문에 `python src/main.py`
직접 실행은 동작하지 않을 수 있다).

## 아키텍처 한눈에 보기

```
project_loader → image_classifier → script_generator → shot_planner
  → motion_planner → subtitle_generator → renderer → thumbnail_generator
  → caption_generator
```

- 오케스트레이션: `src/pipeline/orchestrator.py`가 위 순서로 각 단계를 실행하고,
  단계별 성공/실패를 `logs/run-log.md`에 남긴다. 한 단계가 실패해도 어디서
  실패했는지 로그로 추적 가능하게 하는 것이 원칙이다.
- 데이터 모델: `src/models/`(Project/Shot/Subtitle/RenderJob).
- 설정 분리: `config/*.yaml`을 바꾸면 코드 수정 없이 컷 길이/자막/모션/렌더링
  결과가 바뀐다. 톤(emotional/informative/review/ad) → 스타일 프리셋 매핑은
  `config/style-rules.yaml`의 `tone_to_style`에 있다.
- 확장 인터페이스: `src/adapters/`에 LLM / image-to-video / storage 어댑터가
  분리돼 있다. `ANTHROPIC_API_KEY`가 없으면 자동으로 규칙 기반 템플릿 폴백을
  쓰므로, 파이프라인은 항상 오프라인에서도 끝까지 동작해야 한다 — 이 불변식을
  깨는 변경(예: LLM 응답이 없으면 예외를 던지게 바꾸는 것)은 피할 것.

## 자주 하는 작업

- **새 숙소 프로젝트로 릴스 만들기**: `skills/hotel-reel-skill.md`의 "명령 매핑"
  표를 따른다. `input.md`가 없으면 사용자에게 필요한 필드를 물어보고 생성한다.
- **사진 없이 구조만 테스트**: `python3 scripts/generate_mock_images.py --project <경로>`
  로 mock 이미지를 만든 뒤 `--skip-render`로 빠르게 데이터 단계만 검증한다.
- **렌더링 결과가 이상할 때**: `logs/ffmpeg.log`를 먼저 확인한다. 자막은
  libass(`ass` 필터)로 번인되며, `src/pipeline/renderer.py`의
  `write_ass_file`(폭 기준 폰트 자동 축소 로직)과
  `config/subtitle-template.yaml`의 `max_chars_per_line`를 함께 살펴본다.
  키워드 강조 색상은 `style-rules.yaml`의 `subtitle.tone`(clean/bold/friendly)
  값을 `subtitle-template.yaml`의 `tone_emphasis_color`에서 찾아 적용한다 —
  이 둘의 키가 어긋나면 강조색이 항상 기본값으로 고정되니 주의할 것
  (실제로 한 번 이 버그가 있었다).
- **컷 길이가 목표 영상 길이와 안 맞을 때**: `config/style-rules.yaml`의
  `average_shot_duration`/`min_shot_duration`/`max_shot_duration`이
  `src/pipeline/script_generator.py`의 `SCENE_COUNT_BY_LENGTH`와 정합적인지
  확인한다 (컷 수 × 평균 길이 ≈ 목표 길이가 되어야 클램핑으로 인한 길이 손실이
  적다).
- **편집 스타일 프리셋 추가**: `config/style-rules.yaml`의 `styles:` 아래 새
  키를 추가하고 `tone_to_style`에 매핑하면 된다. 코드 변경 불필요.

## 테스트/검증 방법

이 저장소에는 별도 테스트 프레임워크가 없다. 변경 후에는 아래로 end-to-end
검증하는 것을 권장한다:

```bash
python -m src.main --project ./sample_projects/sample_hotel --skip-render   # 빠른 회귀 확인
python -m src.main --project ./sample_projects/sample_hotel                 # 실제 렌더링까지
ffprobe -v error -show_entries format=duration -show_entries stream=width,height output/reel-final.mp4
```

렌더링된 mp4에서 프레임을 뽑아 자막이 화면 안에 들어오는지 시각적으로 확인하는
것도 유용하다:

```bash
ffmpeg -y -i sample_projects/sample_hotel/output/reel-final.mp4 \
  -vf "select='eq(n\,90)'" -vsync 0 /tmp/check_frame.jpg
```

## 하지 말아야 할 것

- `ANTHROPIC_API_KEY` 없이도 되던 동작을 API 키 필수로 바꾸지 말 것 (오프라인
  100% 동작이 핵심 요구사항).
- `config/*.yaml`에 있어야 할 값(폰트 경로, 컷 길이, 모션 파라미터 등)을
  Python 코드에 하드코딩하지 말 것 — 재사용성/템플릿화 원칙을 깨뜨린다.
- 렌더링 단계에서 실패를 조용히 삼키지 말 것 — `RunLogger`로 반드시 남긴다.
