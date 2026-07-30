#!/usr/bin/env python3
"""Fetch MH45 / MH61 Selig coordinates into this folder.

BLOCKED offline: does not write placeholder .dat files.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent

AIRFOILS = {
    "mh45.dat": [
        "https://m-selig.ae.illinois.edu/ads/coord/mh45.dat",
        "http://airfoiltools.com/airfoil/seligdatfile?airfoil=mh45-il",
    ],
    "mh61.dat": [
        "https://m-selig.ae.illinois.edu/ads/coord/mh61.dat",
        "http://airfoiltools.com/airfoil/seligdatfile?airfoil=mh61-il",
    ],
}


def fetch(url: str, timeout: float = 20.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "NULLXES-BLACK-DEATH/alpha"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def main() -> int:
    failed: list[str] = []
    for name, urls in AIRFOILS.items():
        dest = OUT / name
        ok = False
        for url in urls:
            try:
                data = fetch(url)
                if len(data) < 50:
                    continue
                dest.write_bytes(data)
                print(f"OK {name} <- {url}")
                ok = True
                break
            except Exception as exc:  # noqa: BLE001
                print(f"FAIL {name} {url}: {exc}")
        if not ok:
            failed.append(name)
            print(f"BLOCKED: could not fetch {name} — no stub written")
    if failed:
        print(f"BLOCKED: missing airfoils: {failed}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
