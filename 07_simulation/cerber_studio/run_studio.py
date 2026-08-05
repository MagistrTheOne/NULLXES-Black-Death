#!/usr/bin/env python3
"""NULLXES CERBER Studio — entrypoint.

  python run_studio.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from studio.app import StudioWindow

    print("NULLXES CERBER Studio v1 · VIRTUAL WORLD · NOT TWIN")
    app = QApplication(sys.argv)
    app.setApplicationName("NULLXES CERBER Studio")
    win = StudioWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
