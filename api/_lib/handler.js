// 공통 POST-only 핸들러 래퍼. 에러를 일관된 JSON 형태로 응답한다.
export function withHandler(fn) {
  return async (req, res) => {
    if (req.method !== 'POST') {
      res.status(405).json({ error: 'POST 요청만 지원합니다.' })
      return
    }
    try {
      await fn(req, res)
    } catch (err) {
      console.error(err)
      res.status(500).json({
        error: err?.message || '서버 오류가 발생했습니다.',
        raw: err?.raw,
      })
    }
  }
}
