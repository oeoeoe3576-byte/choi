"""스토리지 어댑터.

MVP는 로컬 파일시스템만 지원한다. 추후 S3/GCS 등으로 확장할 때
이 인터페이스(save/load/list/exists)만 구현하면 pipeline 코드는 그대로 재사용 가능하다.
"""

from __future__ import annotations

from pathlib import Path


class LocalStorageAdapter:
    provider = "local"

    def save_bytes(self, path: Path, data: bytes) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def load_bytes(self, path: Path) -> bytes:
        return path.read_bytes()

    def list_files(self, directory: Path, pattern: str = "*") -> list[Path]:
        if not directory.exists():
            return []
        return sorted(directory.glob(pattern))

    def exists(self, path: Path) -> bool:
        return path.exists()


def get_storage_adapter() -> LocalStorageAdapter:
    # 2차 확장: 환경변수(STORAGE_PROVIDER)에 따라 S3StorageAdapter 등을 반환하도록 교체 가능
    return LocalStorageAdapter()
