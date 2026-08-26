"""엔트리포인트: python -m src.main [옵션]"""

from __future__ import annotations

import sys

from src.cli import main

if __name__ == "__main__":
    sys.exit(main())
