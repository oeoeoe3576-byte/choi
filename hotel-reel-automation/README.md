# hotel-reel-automation

숙소(호텔/게스트하우스/독채) 사진 폴더 + 기본 정보만 넣으면, 9:16 숏폼 릴스를
**대본 → 컷 편집 계획 → 이미지 모션 → 자막 → 최종 mp4 → 썸네일 → 인스타 캡션**까지
자동으로 만들어주는 Claude Code용 재사용형 자동화 파이프라인이다.

거대한 웹서비스가 아니라, **Claude Code 안에서 바로 실행 가능한 워크플로우**로
설계했다. 숙소별로 폴더 하나만 만들면 반복 사용할 수 있다.

```
"이 숙소 폴더로 릴스 만들어줘."
"이 폴더 사진으로 20초짜리 감성형 숙소 영상 만들어줘."
"이 프로젝트 내일 오전 9시에 렌더링되게 예약해줘."
"새 레퍼런스 반영해서 편집 규칙 업데이트해줘."
```

## 데모: sample_projects/sample_hotel

`sample_projects/sample_hotel/`에는 mock 이미지 12장으로 만든 실제 실행 결과가
그대로 들어있다 (`output/reel-final.mp4`, `output/thumbnail.jpg`, `script.md`,
`caption.txt` 등). 사진 없이도 구조가 어떻게 동작하는지 바로 확인할 수 있다.

## 폴더 구조

```
hotel-reel-automation/
├─ CLAUDE.md                 # Claude Code용 저장소 가이드
├─ README.md                 # 이 문서
├─ requirements.txt
├─ .env.example
│
├─ skills/
│  └─ hotel-reel-skill.md     # Claude Code Skill 정의 (자연어 -> CLI 매핑)
│
├─ prompts/                   # LLM 연결 시 사용하는 프롬프트 템플릿
│  ├─ script-prompt.md
│  ├─ caption-prompt.md
│  ├─ image-tagging-prompt.md
│  └─ reference-analysis-prompt.md
│
├─ config/                    # 코드 수정 없이 결과를 바꾸는 설정 파일들
│  ├─ style-rules.yaml         # 톤별 컷 길이/전환/모션 성향
│  ├─ subtitle-template.yaml   # 자막 위치/폰트/강조 규칙
│  ├─ motion-presets.yaml      # 모션 프리셋 파라미터
│  ├─ render-config.yaml       # 해상도/코덱/폰트 경로
│  └─ scheduler-config.yaml    # 예약 실행 설정
│
├─ src/
│  ├─ main.py / cli.py         # 엔트리포인트
│  ├─ pipeline/                # 단계별 파이프라인 모듈
│  ├─ models/                  # 데이터 모델 (Project/Shot/Subtitle/RenderJob)
│  ├─ utils/                   # 파일/ffmpeg/시간/검증 유틸
│  └─ adapters/                # LLM / image-to-video / storage 확장 인터페이스
│
├─ templates/                  # 릴스/자막/썸네일 스키마 템플릿(JSON)
├─ sample_projects/sample_hotel/
└─ scripts/                    # 쉘 래퍼 (run/schedule/update-style-rules)
```

## 설치 (macOS / Linux)

```bash
cd hotel-reel-automation
python3 -m venv .venv && source .venv/bin/activate   # 선택
pip install -r requirements.txt

# ffmpeg
# macOS: brew install ffmpeg
# Debian/Ubuntu: sudo apt-get install -y ffmpeg

# 한글 자막 렌더링을 위한 폰트 (Nanum 계열 권장)
# macOS: 시스템 기본 한글 폰트로도 동작 (config/render-config.yaml의
#         font_path_candidates에 macOS 폰트 경로를 추가하면 됨)
# Debian/Ubuntu: sudo apt-get install -y fonts-nanum
```

`ANTHROPIC_API_KEY`는 선택 사항이다. 없어도 규칙 기반 템플릿으로 대본/캡션이
100% 생성된다 (오프라인 동작). 설정하면 대본/캡션 품질이 실제 LLM 수준으로
올라간다.

```bash
cp .env.example .env   # 필요 시 ANTHROPIC_API_KEY 채우기
```

## 빠른 시작

```bash
# 1) 프로젝트 폴더 만들기 (숙소마다 하나씩)
mkdir -p my_hotel/images
cp ~/사진들/*.jpg my_hotel/images/

# 2) input.md 작성 (sample_projects/sample_hotel/input.md 참고)
cat > my_hotel/input.md << 'EOF'
hotel_name: My Hotel
location: 제주 애월
one_liner: 바다가 보이는 감성 독채
video_length: 20
tone: emotional
highlight_points:
  - 오션뷰가 예쁨
  - 프라이빗한 독채
  - 조식 만족도가 높음
EOF

# 3) 실행
python -m src.main --project ./my_hotel
```

실제 사진 없이 구조부터 확인하고 싶다면:

```bash
python3 scripts/generate_mock_images.py --project ./my_hotel
python -m src.main --project ./my_hotel --skip-render   # 렌더링 없이 데이터만
python -m src.main --project ./my_hotel                 # 실제 mp4까지
```

## CLI 사용법

```bash
# 기본 실행
python -m src.main --project ./sample_projects/sample_hotel

# 톤/길이 오버라이드
python -m src.main --project ./sample_projects/sample_hotel --tone review --length 15

# 렌더링 없이 구조/데이터만 생성 (빠른 반복 테스트용)
python -m src.main --project ./sample_projects/sample_hotel --skip-render

# 예약 실행 (미래 시각) — 등록만 됨. 실제 실행은 아래 "예약 실행" 절 참고
python -m src.main --project ./sample_projects/sample_hotel --schedule "2026-08-28 09:00"
python -m src.main --list-schedules
python -m src.main --cancel-schedule job_xxxxxxxx

# 레퍼런스 반영해서 스타일 규칙 업데이트
python -m src.main --update-style-rules --reference-dir ./sample_projects/sample_hotel/references
```

쉘 래퍼(`scripts/`)로도 동일하게 실행 가능:

```bash
scripts/run_project.sh ./sample_projects/sample_hotel --tone ad --length 15
scripts/schedule_project.sh ./sample_projects/sample_hotel "2026-08-28 09:00" --install-cron
scripts/update_style_rules.sh ./sample_projects/sample_hotel/references
```

## 예약 실행 구조

상시 데몬 없이 동작한다:
1. `--schedule`로 등록 → `scheduled-jobs.json`에 저장.
2. 등록 시점에 예약 시각이 이미 지났다면 즉시 실행된다.
3. 미래 시각이면, `scripts/schedule_project.sh ... --install-cron`으로 cron에
   `python -m src.main --run-due`를 5분 간격으로 등록해두면 실제 시각에 렌더링된다
   (macOS는 cron에 디스크 접근 권한을 별도로 허용해야 할 수 있다).

## 산출물

프로젝트 폴더 안에 생성된다:

| 파일 | 설명 |
|---|---|
| `image-analysis.json` | 이미지 분류/우선순위 |
| `script.md` / `script.json` | 대본 (hook/scenes/closing/cta) |
| `edit-plan.json` | 컷별 이미지/길이/전환/자막 매칭 |
| `motion-plan.json` | 컷별 모션 + image-to-video 적용 여부 판단 |
| `subtitles.json` / `subtitles.srt` | 자막 타이밍/텍스트 |
| `caption.txt` | 인스타 캡션 (후킹형/정보형/해시태그) |
| `output/reel-final.mp4` | 최종 9:16 영상 |
| `output/thumbnail.jpg` | 썸네일 |
| `logs/run-log.md`, `logs/ffmpeg.log` | 실행 로그 (실패 단계 추적용) |

## 편집 스타일을 바꾸고 싶을 때

코드를 건드릴 필요 없이 `config/*.yaml`만 수정하면 된다:
- 컷 길이/전환/모션 성향 → `config/style-rules.yaml`
- 자막 위치/폰트/강조 규칙 → `config/subtitle-template.yaml`
- 모션 세부 파라미터 → `config/motion-presets.yaml`
- 렌더링 해상도/코덱/폰트 경로 → `config/render-config.yaml`

레퍼런스 영상을 분석해 규칙을 늘리고 싶다면, `<레퍼런스 폴더>/notes.yaml`을
작성(`prompts/reference-analysis-prompt.md` 참고)한 뒤:

```bash
python -m src.main --update-style-rules --reference-dir <레퍼런스 폴더>
```

`style-rules.yaml`의 해당 스타일에 병합되고, `reference_notes`에 이력이 쌓인다.

## 렌더링 엔진으로 FFmpeg를 선택한 이유

- CapCut 등 GUI 자동화 클릭 방식보다 환경 의존성이 적다 (헤드리스 서버/컨테이너에서 안정적).
- 완전히 코드/설정 파일로 파라미터화할 수 있다 — config만 바꾸면 결과가 바뀐다.
- 컷마다 `scale→crop→zoompan(모션)→fade(전환)→drawtext(자막)` 필터 체인을 만들고,
  concat demuxer로 이어붙인 뒤 mp4로 인코딩한다 (`src/pipeline/renderer.py`).

## 향후 확장 포인트 (구조는 이미 열어둠)

- **레퍼런스 영상 자동 분석**: 현재는 사람이 정리한 `notes.yaml`을 병합하는 방식.
  비전/영상 분석 모델을 붙이면 `prompts/reference-analysis-prompt.md` 기반으로
  완전 자동화할 수 있다 (`src/pipeline/reference_updater.py`).
- **AI Image-to-Video**: `src/adapters/image_to_video_adapter.py`가 인터페이스를
  잡아두었다. 지금은 항상 `use_image_to_video=false`(stub)를 반환하며, 실제
  provider(Runway/Kling/Luma 등)를 연결하면 수영장 물결/커튼 흔들림 등 특정 컷만
  선별적으로 영상화할 수 있다.
- **비전 기반 이미지 태깅**: `src/pipeline/image_classifier.py`의
  `classify_with_vision()` 스텁을 구현하면 파일명 규칙 대신 실제 이미지 내용
  기반 분류로 업그레이드된다 (`prompts/image-tagging-prompt.md`).
- **예약 → 업로드 자동화**: 현재는 렌더링 예약까지만 지원한다. 인스타/틱톡
  업로드 자동화는 `src/pipeline/scheduler.py`의 job 완료 훅에 이어붙이면 된다.
- **배치 렌더링 / 다국어 버전 / 음성 나레이션**: `orchestrator.run_pipeline()`을
  여러 프로젝트/언어에 대해 반복 호출하는 얇은 래퍼를 추가하면 된다 (구조 변경 불필요).
- **스토리지 교체(S3 등)**: `src/adapters/storage_adapter.py` 인터페이스만
  구현하면 파이프라인 코드는 그대로 재사용된다.

## 설계 원칙

1. 웹앱보다 워크플로우 우선 — Claude Code 안에서 바로 도는 CLI가 먼저다.
2. MVP 우선 — 실제로 mp4가 나오는 구조를 완성하는 것이 최우선이었다.
3. 템플릿화 — 자막/컷/모션/캡션 규칙은 전부 `config/`, `prompts/` 파일로 분리.
4. 재사용성 — 프로젝트 폴더 단위로 숙소마다 반복 사용 가능.
5. 실패해도 로그를 남긴다 — `logs/run-log.md`에 단계별 성공/실패가 기록된다.
6. 하드코딩 최소화 — 톤/길이/스타일에 따라 파라미터가 자동 조정된다.
