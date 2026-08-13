#!/usr/bin/env python3
"""NULLXES CERBER Studio — entrypoint.

  python run_studio.py              engineering IDE
  python run_studio.py --engineering
  python run_studio.py --demo       product menu / Full HD
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="NULLXES CERBER Studio")
    ap.add_argument("--demo", action="store_true", help="product UI, borderless Full HD")
    ap.add_argument("--engineering", action="store_true", help="engineering IDE (default)")
    args = ap.parse_args()
    demo = bool(args.demo) and not bool(args.engineering)

    from PySide6.QtWidgets import QApplication

    from studio.config.settings import UserSettings

    app = QApplication(sys.argv)
    app.setApplicationName("NULLXES CERBER Studio")
    settings = UserSettings.load()

    if demo:
        from studio.product_app import ProductWindow, configure_product_logging

        configure_product_logging()

        def _hook(ty, val, tb) -> None:
            logging.getLogger("cerber_studio").exception("unhandled", exc_info=(ty, val, tb))

        sys.excepthook = _hook
        win = ProductWindow(settings)
        win.show()
        return app.exec()

    from studio.app import StudioWindow

    print("NULLXES CERBER Studio v1 · VIRTUAL WORLD · NOT TWIN")
    win = StudioWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
