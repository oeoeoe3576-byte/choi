// 브라우저 localStorage 기반 저장소.
// "내 성과" 기록과 "터진 글 분석"으로 뽑은 구조 템플릿을 저장한다.
// 나중에 실제 백엔드(DB)로 옮길 때는 이 파일의 함수 시그니처만 유지하면 된다.

const KEYS = {
  posts: 'tve.posts.v1',
  templates: 'tve.templates.v1',
}

function safeGet(key) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function safeSet(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
    return true
  } catch {
    return false
  }
}

function uid() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

// ── 게시 성과 기록 ──────────────────────────────────────────
export function getPosts() {
  return safeGet(KEYS.posts)
}

export function addPost(post) {
  const posts = getPosts()
  const record = {
    id: uid(),
    createdAt: new Date().toISOString(),
    viralTypeId: post.viralTypeId ?? null,
    length: post.length ?? null,
    hookText: post.hookText ?? '',
    body: post.body ?? '',
    views: Number(post.views) || 0,
    likes: Number(post.likes) || 0,
    replies: Number(post.replies) || 0,
    reposts: Number(post.reposts) || 0,
    quotes: Number(post.quotes) || 0,
    followerDelta: Number(post.followerDelta) || 0,
    memo: post.memo ?? '',
  }
  posts.unshift(record)
  safeSet(KEYS.posts, posts)
  return record
}

export function deletePost(id) {
  const posts = getPosts().filter((p) => p.id !== id)
  safeSet(KEYS.posts, posts)
  return posts
}

export function updatePost(id, patch) {
  const posts = getPosts().map((p) => (p.id === id ? { ...p, ...patch } : p))
  safeSet(KEYS.posts, posts)
  return posts
}

// ── 터진 글 분석 결과(구조 템플릿) ──────────────────────────
export function getTemplates() {
  return safeGet(KEYS.templates)
}

export function addTemplate(template) {
  const templates = getTemplates()
  const record = {
    id: uid(),
    createdAt: new Date().toISOString(),
    ...template,
  }
  templates.unshift(record)
  safeSet(KEYS.templates, templates)
  return record
}

export function deleteTemplate(id) {
  const templates = getTemplates().filter((t) => t.id !== id)
  safeSet(KEYS.templates, templates)
  return templates
}

// ── 집계: 내 계정만의 바이럴 공식 ────────────────────────────
// 참여도 지표: replies에 가장 큰 가중치(작성자 답글 유도가 42% 더 높은 참여를 만든다는
// 벤치마크를 반영), reposts/quotes는 확산, likes는 보조 지표로 사용.
export function engagementScore(post) {
  const views = Math.max(post.views, 1)
  return (
    (post.replies * 3 + post.reposts * 2 + post.quotes * 2 + post.likes * 1) / views
  ) * 1000
}

export function aggregateByViralType() {
  const posts = getPosts()
  const groups = new Map()
  for (const post of posts) {
    if (!post.viralTypeId) continue
    const g = groups.get(post.viralTypeId) ?? { viralTypeId: post.viralTypeId, posts: [] }
    g.posts.push(post)
    groups.set(post.viralTypeId, g)
  }
  return Array.from(groups.values())
    .map((g) => ({
      viralTypeId: g.viralTypeId,
      count: g.posts.length,
      avgViews: avg(g.posts.map((p) => p.views)),
      avgEngagement: avg(g.posts.map(engagementScore)),
    }))
    .sort((a, b) => b.avgEngagement - a.avgEngagement)
}

export function aggregateByLength() {
  const posts = getPosts()
  const groups = new Map()
  for (const post of posts) {
    if (!post.length) continue
    const g = groups.get(post.length) ?? { length: post.length, posts: [] }
    g.posts.push(post)
    groups.set(post.length, g)
  }
  return Array.from(groups.values())
    .map((g) => ({
      length: g.length,
      count: g.posts.length,
      avgViews: avg(g.posts.map((p) => p.views)),
      avgEngagement: avg(g.posts.map(engagementScore)),
    }))
    .sort((a, b) => b.avgEngagement - a.avgEngagement)
}

function avg(nums) {
  if (!nums.length) return 0
  return nums.reduce((a, b) => a + b, 0) / nums.length
}
