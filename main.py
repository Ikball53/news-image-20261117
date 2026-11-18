"""Copy the finished front page into the harness output folder.

The artwork itself lives in this repository as entry.png; this program only
places an exact copy at /output/entry.png. It reads and writes bytes only,
takes no input, touches no network, and produces identical output on every
run. Standard library only.
"""

from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "entry.png"
TARGET = Path("/output/entry.png")


def place_page() -> int:
    payload = SOURCE.read_bytes()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_bytes(payload)
    placed = TARGET.read_bytes()
    if placed != payload:
        raise SystemExit("copy mismatch: /output/entry.png differs from entry.png")
    return len(payload)


if __name__ == "__main__":
    written = place_page()
    print(f"entry.png placed at /output/entry.png ({written} bytes)")
