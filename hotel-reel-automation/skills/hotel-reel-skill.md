---
name: hotel-reel-automation
description: >
  숙소(호텔/게스트하우스/독채) 사진 폴더와 기본 정보만으로 9:16 숏폼 릴스(대본,
  컷 편집 계획, 자막, 최종 mp4, 썸네일, 인스타 캡션)를 자동 생성한다. 사용자가
  "이 숙소 폴더로 릴스 만들어줘", "이 폴더 사진으로 O초짜리 감성형/정보형/후기형/
  광고형 숙소 영상 만들어줘", "내일 오전 9시에 렌더링되게 예약해줘", "새 레퍼런스
  반영해서 편집 규칙 업데이트해줘"라고 말할 때 사용한다.
---

# Hotel Reel Automation Skill

숙소 사진 기반 숏폼 릴스를 자동 제작하는 Claude Code 워크플로우다. 이 파일은
Claude Code가 자연어 요청을 `hotel-reel-automation/` 파이프라인 CLI 호출로
변환하기 위한 지침이다.

## 언제 이 Skill을 쓰는가

- 사용자가 숙소 사진이 담긴 폴더를 가리키며 "릴스/숏폼/영상 만들어줘"라고 할 때
- 영상 길이(15/20/30초)나 톤(감성형/정보형/후기형/광고형)을 지정할 때
- "예약해서 렌더링해줘" 처럼 특정 시각 실행을 요청할 때
- "레퍼런스 반영해서 스타일/편집 규칙 업데이트해줘"라고 할 때

## 사전 준비 확인

1. 이 저장소의 `hotel-reel-automation/` 디렉터리가 작업 디렉터리 기준으로
   어디에 있는지 확인한다 (`find . -maxdepth 3 -name hotel-reel-automation`).
2. 최초 1회, 의존성이 설치돼 있는지 확인한다:
   ```bash
   cd hotel-reel-automation
   pip install -r requirements.txt
   which ffmpeg || (echo "ffmpeg가 없습니다. apt-get install -y ffmpeg 등으로 설치하세요.")
   ```
3. 자막은 기본적으로 손글씨 폰트(Nanum Pen Script)로 번인된다. `fonts-nanum`
   뿐 아니라 `fonts-nanum-extra`도 있어야 손글씨 계열이 설치된다. 없으면 안내한다:
   ```bash
   fc-list | grep -qi "nanum pen" || echo "손글씨 폰트가 없습니다. 'apt-get install -y fonts-nanum fonts-nanum-extra' 권장."
   ```

## 프로젝트 폴더 규칙

사용자가 가리킨 "숙소 폴더"는 아래 구조를 따라야 한다 (없는 파일/폴더는 자동 생성/보완됨):

```
<프로젝트 폴더>/
├─ input.md          # 필수. 숙소명/위치/톤/길이/하이라이트 등 (YAML 문법)
├─ images/            # 필수. 숙소 사진 8장 이상 권장
├─ references/        # 선택. 레퍼런스 영상/메모
├─ output/            # 자동 생성 (렌더 결과)
└─ logs/              # 자동 생성 (실행 로그)
```

사용자가 아직 `input.md`가 없는 폴더를 준다면, 대화로 아래 항목을 물어보고
`input.md`를 생성한 뒤 진행한다:
- hotel_name, location, one_liner
- highlight_points (3~5개)
- video_length (15|20|30, 기본 20)
- tone (emotional|informative|review|ad, 기본 emotional)
- price_info(선택), cta_type(선택, 기본 save)

이미지가 아예 없다면(구조 테스트 목적인 경우) 아래로 mock 이미지를 만들 수 있다:
```bash
python3 scripts/generate_mock_images.py --project <프로젝트 폴더>
```

## 표준 실행 흐름 — 대본 먼저 확인받고 렌더링

**새 릴스를 만들 때는 곧바로 최종 렌더링까지 가지 말고, 아래 2단계로 진행하는
것이 기본값이다** (사용자가 "확인 없이 바로 만들어줘"라고 명시하지 않는 한):

**1단계 — 대본만 생성해서 보여준다**
```bash
python -m src.main --project <경로> --skip-render
```
이 명령은 렌더링 없이 `script.md`까지만 만든다. `script.md`(또는
`script.json`의 hook/scenes/closing/cta)를 읽어서, 아래처럼 **줄바꿈마다
불릿으로** 사용자에게 그대로 보여주고 확인을 요청한다:

```
* Porto, Portugal에서 감성 숙소 찾는다면 여기 저장해두세요.   (hook)
* 강변 뷰가 예뻐요.                                          (scene)
* 객실 인테리어가 감성적이에요.                                (scene)
* ...
* Porto, Portugal 숙소 고민 중이라면 참고해보세요.             (closing)
* 저장해두고 여행 때 꺼내보세요.                               (cta)

이대로 진행할까요? 수정하고 싶은 줄이 있으면 알려주세요.
```

**2단계 — 확인 후, 그 대본 그대로 렌더링한다**

- 사용자가 그대로 좋다고 하면: `python -m src.main --project <경로> --reuse-script`
  (주의: `--reuse-script` 없이 다시 실행하면 대본을 처음부터 다시 만들어서,
  `ANTHROPIC_API_KEY`가 설정된 LLM 모드에서는 방금 승인받은 문구와 미묘하게
  달라질 수 있다. 반드시 `--reuse-script`를 써서 "승인한 그대로"가 보장되게 한다.)
- 사용자가 특정 줄을 고쳐달라고 하면: `<프로젝트 폴더>/script.json`의 해당
  필드(`hook`/`scenes`의 배열 항목/`closing`/`cta`)를 요청받은 문구로 직접
  수정한 뒤, 같은 방식으로 다시 보여주고 재확인받는다. 확인되면
  `--reuse-script`로 렌더링한다.
- `--reuse-script` 사용 시 `--tone`/`--length`는 원칙적으로 다시 주지 않는다
  (이미 승인된 대본은 1단계에서 쓴 톤/길이에 맞춰 만들어졌기 때문).

톤/길이를 바꾸고 싶다는 요청이면 1단계로 돌아가 `--tone`/`--length`를 바꿔
다시 대본부터 생성하고 재확인 받는다.

## 명령 매핑

| 사용자 요청 예시 | 실행할 CLI 명령 |
|---|---|
| "이 폴더로 릴스 만들어줘" (표준 흐름 1단계) | `python -m src.main --project <경로> --skip-render` |
| "이대로 진행해줘" (표준 흐름 2단계, 확인 후) | `python -m src.main --project <경로> --reuse-script` |
| "확인 없이 바로 만들어줘" | `python -m src.main --project <경로>` |
| "20초짜리 감성형으로 만들어줘" | `python -m src.main --project <경로> --length 20 --tone emotional --skip-render` (먼저 대본 확인) |
| "내일 오전 9시에 렌더링 예약해줘" | `python -m src.main --project <경로> --schedule "YYYY-MM-DD HH:MM"` |
| "예약 목록 보여줘" | `python -m src.main --list-schedules` |
| "예약 job_xxxx 취소해줘" | `python -m src.main --cancel-schedule job_xxxx` |
| "예약된 것들 지금 실행해줘" (cron 대신 수동 트리거) | `python -m src.main --run-due` |
| "새 레퍼런스 반영해서 편집 규칙 업데이트해줘" | `python -m src.main --update-style-rules --reference-dir <레퍼런스 경로>` |

모든 명령은 `hotel-reel-automation/` 디렉터리를 작업 디렉터리로 실행해야 한다
(`python -m src.main ...` 형태는 패키지 상대 import를 쓰기 때문).

## 실행 후 할 일

1. CLI가 반환한 JSON의 `steps`를 확인해 어떤 단계가 실패했는지 파악한다.
   실패한 단계가 있으면 `<프로젝트 폴더>/logs/run-log.md`와
   `logs/ffmpeg.log`(렌더링 실패 시)를 읽어 원인을 사용자에게 설명한다.
2. `--skip-render`(1단계) 성공 시: 위 "표준 실행 흐름"대로 대본을 보여주고
   확인을 기다린다 — 이 시점에는 아직 최종 산출물을 전달하지 않는다.
3. 렌더링(2단계, `--reuse-script` 또는 확인 없이 바로 실행한 경우)까지
   성공하면 아래 산출물을 사용자에게 안내한다:
   - `script.md` / `script.json` — 대본
   - `edit-plan.json` — 컷 편집 계획
   - `motion-plan.json` — 컷별 모션
   - `subtitles.json` / `subtitles.srt` — 자막
   - `caption.txt` — 인스타 캡션 3종
   - `output/reel-final.mp4` — 최종 영상
   - `output/thumbnail.jpg` — 썸네일
4. 결과물 파일(특히 `output/reel-final.mp4`)은 SendUserFile 등으로 사용자에게
   바로 전달하는 것을 우선 고려한다.

## 편집 규칙을 바꾸고 싶을 때

코드 수정 없이 아래 파일만 바꾸면 결과가 바뀐다:
- `config/style-rules.yaml` — 톤별 컷 길이/전환/모션 성향
- `config/subtitle-template.yaml` — 자막 위치/폰트/강조 규칙
- `config/motion-presets.yaml` — 모션 프리셋 파라미터
- `config/render-config.yaml` — 해상도/코덱/폰트 경로 등 렌더링 설정

레퍼런스 영상에서 얻은 규칙은 `<레퍼런스 폴더>/notes.yaml`에 정리한 뒤
`--update-style-rules --reference-dir <경로>`로 병합한다. `notes.yaml` 포맷은
`prompts/reference-analysis-prompt.md`에 있다.

## 알아둘 것

- `ANTHROPIC_API_KEY`가 설정돼 있으면 대본/캡션 생성이 실제 LLM 호출로
  업그레이드된다. 없으면 규칙 기반 템플릿으로 오프라인 동작한다 (기본값).
- image-to-video(수영장 물결 등 AI 영상화)는 MVP에서 기본 비활성화된 스텁이다.
  `--image-to-video` 플래그로 판단 로직만 활성화해볼 수 있다 (실제 변환은 미구현).
- 예약(`--schedule`)은 상시 데몬을 띄우지 않는다. 미래 시각으로 예약한 경우
  실제로 그 시각에 실행되게 하려면 `scripts/schedule_project.sh`를 참고해
  cron/at에 `python -m src.main --run-due`를 등록해야 한다고 사용자에게 안내한다.
