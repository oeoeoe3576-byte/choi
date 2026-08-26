"""컷 수에 맞춰 대표 이미지를 선택/정렬하는 모듈.

규칙:
  - 첫 컷은 exterior/lobby 등 임팩트 있는 장면 우선
  - 같은 scene_type이 연속으로 붙지 않게 배치
  - narrative_priority 순서를 뼈대로 하되, 화질 점수(quality_score)가 높은 것을 우선
  - 이미지 수가 필요한 컷 수보다 적으면 재사용(순환)한다
"""

from __future__ import annotations

import itertools


def select_shot_images(analysis: list[dict], shot_count: int) -> list[dict]:
    if not analysis:
        return []

    # scene_type별로 화질 좋은 순으로 정렬된 큐를 만든다
    by_type: dict[str, list[dict]] = {}
    for rec in analysis:
        by_type.setdefault(rec["scene_type"], []).append(rec)
    for records in by_type.values():
        records.sort(key=lambda r: (-r["quality_score"], r["order_in_folder"]))

    # narrative_priority 순으로 scene_type 순서를 정한다
    type_order = sorted(by_type.keys(), key=lambda t: by_type[t][0]["narrative_priority"])
    type_cycle = itertools.cycle(type_order)

    selected: list[dict] = []
    used_per_type_idx = {t: 0 for t in type_order}
    last_type = None

    attempts = 0
    max_attempts = shot_count * len(type_order) * 3 + 10
    while len(selected) < shot_count and attempts < max_attempts:
        attempts += 1
        scene_type = next(type_cycle)
        if scene_type == last_type and len(type_order) > 1:
            continue  # 연속 중복 방지 (선택지가 있을 때만)

        idx = used_per_type_idx[scene_type]
        pool = by_type[scene_type]
        record = pool[idx % len(pool)]
        used_per_type_idx[scene_type] += 1

        selected.append(record)
        last_type = scene_type

    # 그래도 못 채웠으면 (극단적으로 이미지 종류가 1개뿐인 경우) 단순 반복으로 채운다
    if len(selected) < shot_count:
        flat = analysis
        i = 0
        while len(selected) < shot_count:
            selected.append(flat[i % len(flat)])
            i += 1

    return selected[:shot_count]
