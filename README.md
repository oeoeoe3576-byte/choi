# Threads 바이럴 엔진

"쓰레드 글을 대신 써주는 프로그램"이 아니라 **소재에서 터질 구조를 찾아내고, 실제 게시 성과를 학습해서 내 계정만의 바이럴 공식을 찾아주는 엔진**입니다.

React + Vite 프런트엔드와 Vercel 서버리스 함수(`/api`)로 구성되어 있고, 게시물 생성은 Anthropic Claude API를 호출합니다.

## 핵심 파이프라인

```
소재 입력
  → 소재 분석 (공감성/논쟁성/정보성/경험성/놀라움/댓글가능성/신뢰도 채점)
  → 15개 바이럴 구조 중 적합도 TOP 3 매칭
  → 선택한 구조로 훅(첫 문장) 10개 생성 → Hook Score로 채점 → 상위 3개 제시
  → 훅 선택 → 길이(SHORT/MEDIUM/STORY) + Conversation Trigger 선택 → 본문 생성
  → Hook-Payoff 점수(75점 미만이면 자동 재생성) + AI 말투 감지 + Viral Score 계산
  → "더 세게 / 덜 자극적으로 / 더 자연스럽게 / 다른 훅"으로 재조정
  → 게시 후 "내 성과"에 조회수·좋아요·답글·재게시 수 기록
  → "바이럴 공식" 탭에서 내 계정 기준 고성과 패턴 학습
```

## 화면 구성 (4탭)

1. **글 만들기** — 위 파이프라인 전체를 진행하는 메인 화면
2. **터진 글 분석** — 반응이 좋았던 게시물을 붙여넣으면 문장이 아니라 구조만 추출해 템플릿 DB에 저장 (카피 아님)
3. **내 성과** — 게시 후 실제 수치를 기록. `글 만들기`에서 만든 글을 초안으로 저장하거나 직접 입력 가능
4. **바이럴 공식** — 내 계정의 기록을 바이럴 구조/길이별로 집계해 어떤 조합이 잘 통하는지 보여줌 + 저장된 구조 템플릿 목록

## 폴더 구조

```
api/                    Vercel 서버리스 함수 (Node, ESM)
  _lib/claude.js         Anthropic SDK 호출 + JSON 파싱 공통 로직
  _lib/handler.js         공통 에러 핸들링 래퍼
  analyze.js              소재 분석 → 유형 적합도 TOP3
  hooks.js                훅 후보 생성 + Hook Score 채점
  body.js                 본문 생성/재조정 + Hook-Payoff·Viral Score 계산
  reverse-engineer.js     터진 글 구조 추출

src/
  data/viralTypes.js      15개 바이럴 구조 정의 + 분석 요소 + 길이/CTA 옵션
  data/aiSmell.js          AI 말투 감지용 금지 문구/이모지 목록
  lib/prompts.js           각 단계별 프롬프트 빌더 (서버·클라이언트 공용, 순수 함수)
  lib/scoring.js           점수 계산 (결정적 함수 — LLM은 부분점수만, 합산/가중치/페널티는 코드로 고정)
  lib/store.js             localStorage 기반 성과 기록·구조 템플릿 저장소
  lib/api.js               /api/* 호출 헬퍼
  pages/                   4개 탭 화면
  components/ui.jsx        공용 UI 컴포넌트
```

## 로컬 개발

```bash
npm install
cp .env.example .env   # ANTHROPIC_API_KEY 채워넣기
```

`api/`는 Vercel 서버리스 함수라 `npm run dev`(Vite만 띄우는 경우) 단독으로는 `/api/*` 요청이 동작하지 않습니다. 로컬에서 API까지 함께 확인하려면 Vercel CLI를 쓰세요.

```bash
npm i -g vercel
vercel dev
```

`npm run dev`만 실행하면 프런트엔드 UI/상태 흐름은 확인할 수 있지만 실제 AI 호출은 실패합니다(404).

## 배포 (Vercel)

1. 이 저장소를 Vercel 프로젝트로 연결 (Framework: Vite, 자동 감지됨)
2. 프로젝트 Settings → Environment Variables에 `ANTHROPIC_API_KEY` 등록 (선택: `ANTHROPIC_MODEL`, 기본값 `claude-sonnet-5`)
3. 배포하면 `/api/*`가 서버리스 함수로 자동 인식됩니다 (`vercel.json` 참고)

## 데이터 저장 방식

현재는 개인용 MVP라 "내 성과" 기록과 "터진 글 분석" 구조 템플릿을 **브라우저 localStorage**에 저장합니다 (`src/lib/store.js`). 즉:

- 기기/브라우저별로 데이터가 분리됩니다 (서버에 저장되지 않음)
- 여러 기기에서 데이터를 공유하려면 추후 `store.js`의 함수 시그니처를 유지한 채 실제 DB(Supabase 등)로 교체하면 됩니다

## 설계 원칙 (왜 이렇게 만들었는가)

- **글을 바로 쓰지 않는다**: 소재 분석 → 구조 매칭이 먼저다. 반응할 이유가 없는 소재는 아무리 잘 써도 안 터진다.
- **훅과 본문을 분리해서 각각 채점한다**: 훅만 세고 본문이 못 받쳐주면 신뢰도가 떨어지므로 Hook-Payoff 점수가 75점 미만이면 자동으로 한 번 더 생성한다.
- **총점은 LLM이 아니라 코드가 계산한다** (`src/lib/scoring.js`): LLM은 세부 항목의 부분 점수만 매기고, 가중합과 페널티 적용은 결정적 함수로 고정해 일관성을 유지한다.
- **AI 말투는 규칙 기반으로도 한 번 더 검사한다** (`src/data/aiSmell.js`): 프롬프트로만 막으면 새어나가는 경우가 있어 생성 후 정규식 스캔을 추가로 돌린다.
- **하루 대량 생성 기능은 넣지 않는다**: 대량 생산보다 좋은 글 하나 + 댓글 대화가 더 합리적이라는 설계 원칙을 그대로 반영했다 (자동 예약/대량 큐 기능 없음).
- **터진 글 분석은 문장이 아니라 구조만 뽑는다**: 카피가 아니라 재사용 가능한 패턴 학습이 목적이다.
- **내 계정의 정답을 찾는다**: 인터넷의 일반론이 아니라 "내 성과" 데이터를 축적해 계정별로 다른 고성과 패턴을 학습한다.
