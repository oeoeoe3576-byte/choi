# CLAUDE.md — hotel-reel-automation

이 파일은 Claude Code가 `hotel-reel-automation/` 안에서 작업할 때 참고하는 가이드다.
사람이 "숙소 폴더로 릴스 만들어줘" 같은 요청을 하면, 아래 절차를 따른다.
전체 사용 흐름은 `skills/hotel-reel-skill.md`에 더 자세히 정리돼 있다.

## 이 프로젝트가 하는 일

숙소 사진 폴더 + `input.md`(숙소 정보)를 입력받아, 9:16 숏폼 릴스 제작에 필요한
전 과정(대본 → 컷 편집 계획 → 모션 → mp4 렌더링 → 썸네일 → 인스타 캡션)을
자동으로 처리하는 Python CLI 파이프라인이다. 웹서비스가 아니라 Claude Code /
터미널에서 바로 실행하는 재사용형 워크플로우로 설계됐다.

**핵심은 "사진을 모션이 들어간 영상으로 만드는 것"(renderer.py의 zoompan/
전환/크롭)이지, 자막이 아니다.** 자막은 부가 기능이라 기본적으로 영상에
굽지 않는다(`config/render-config.yaml`의 `subtitle_burn_in.enabled: false`
가 기본값) — 대신 `subtitles.srt`/`subtitles.json`/`script.md`는 항상
생성되므로, 사용자가 CapCut 등에서 직접 자막을 넣을 수 있다.

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

- **새 숙소 프로젝트로 릴스 만들기**: `skills/hotel-reel-skill.md`의 "표준 실행
  흐름"을 따른다 — `--skip-render`로 대본만 먼저 만들어 사용자에게 확인받고,
  승인되면 `--reuse-script`로 그 대본 그대로 렌더링한다(재생성 없이). 사용자가
  대본 일부를 고쳐달라면 `script.json`의 hook/scenes/closing/cta를 직접 수정한
  뒤 다시 확인받고 `--reuse-script`로 진행한다. `input.md`가 없으면 사용자에게
  필요한 필드를 물어보고 생성한다.
- **사진 없이 구조만 테스트**: `python3 scripts/generate_mock_images.py --project <경로>`
  로 mock 이미지를 만든 뒤 `--skip-render`로 빠르게 데이터 단계만 검증한다.
- **렌더링 결과가 이상할 때**: `logs/ffmpeg.log`를 먼저 확인한다. 이미지
  모션(zoompan)이 이상하면 `src/utils/ffmpeg_utils.py`의
  `build_motion_expr`와 `config/motion-presets.yaml`을 본다 — 여기가 이
  파이프라인의 핵심이다. 자막은 기본적으로 꺼져 있지만(`subtitle_burn_in.
  enabled: false`), 켜져 있는 프로젝트라면 libass(`ass` 필터)로 번인되며,
  `src/pipeline/renderer.py`의
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
  키를 추가하고 `tone_to_style`에 매핑하면 된다. 코드 변경 불필요. tone과
  무관하게 특정 프로젝트에만 쓰고 싶으면 `tone_to_style`에 매핑하는 대신
  해당 프로젝트의 `input.md`에 `style_preset: <스타일명>`을 직접 지정한다
  (`src/pipeline/style_resolver.py`가 tone보다 이 값을 우선한다). 컷 수를
  기존 `SCENE_COUNT_BY_LENGTH`(15/20/30초 -> 3/5/8, script_generator.py)와
  다르게 쓰고 싶은 스타일이면 그 스타일 안에 `scene_count_by_length:
  {15: .., 20: .., 30: ..}`를 추가하면 그 스타일에서만 오버라이드된다.
  예시: `insta_reels_hook` 프리셋 — 2026-08에 실제 인스타 릴스 레퍼런스
  10개(컷 경계 자동 감지 + 대표 프레임 시각 분석)를 분석해 반영한 스타일로,
  컷당 1.5초 안팎의 빠른 전환 + 볼드 고딕 자막(`subtitle-template.yaml`의
  `bold_top` 레이아웃) + 가격 훅(`script_rules.hook_template_with_price`,
  `project.price_info` 필요) + 질문형 CTA(`cta_type: question`) 구조다.
  스타일별로 훅/클로징 문구를 완전히 바꾸고 싶으면 `script_rules.
  hook_template` / `hook_template_with_price` / `closing_template`에
  `{place}`/`{hotel}`/`{price}` 플레이스홀더로 문구를 넣으면
  `script_generator.py`가 톤 기반 기본 문구보다 우선해서 쓴다.

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
