"""시간/기간 관련 유틸리티."""

from __future__ import annotations

from datetime import datetime


def parse_schedule_datetime(value: str) -> datetime:
    """'YYYY-MM-DD HH:MM' 형태의 문자열을 datetime으로 파싱한다.

    ISO 형식('YYYY-MM-DDTHH:MM')도 함께 지원한다.
    """
    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    # 마지막 시도: fromisoformat
    return datetime.fromisoformat(value)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def distribute_durations(
    total: float, count: int, first: float, last: float, avg: float,
    min_d: float, max_d: float,
) -> list[float]:
    """총 영상 길이를 count개의 컷에 자연스럽게 분배한다.

    첫/마지막 컷은 first/last를 우선 시도하고, 나머지는 avg를 기준으로 채운 뒤
    총합이 total에 맞도록 비례 보정한다. 각 컷은 [min_d, max_d] 범위를 벗어나지 않는다.
    """
    if count <= 0:
        return []
    if count == 1:
        return [max(min_d, min(max_d, total))]

    durations = [avg] * count
    durations[0] = first
    durations[-1] = last
    durations = [max(min_d, min(max_d, d)) for d in durations]

    current_total = sum(durations)
    if current_total <= 0:
        return durations

    scale = total / current_total
    scaled = [max(min_d, min(max_d, d * scale)) for d in durations]

    # 반올림 오차 보정: 마지막 컷에서 차이를 흡수
    diff = total - sum(scaled)
    scaled[-1] = max(min_d, min(max_d, scaled[-1] + diff))
    return scaled
