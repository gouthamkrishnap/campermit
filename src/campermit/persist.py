import os
from pathlib import Path

DEFAULT_PATH = Path("/etc/campermit/disabled")


def lines(path: Path) -> list[str]:
    try:
        return path.read_text().splitlines()
    except FileNotFoundError:
        return []


def load(path: Path) -> list[str]:
    ids = (line.strip() for line in lines(path))
    return [text for text in ids if text and not text.startswith("#")]


def write(path: Path, rows: list[str]) -> None:
    temp = path.with_name(path.name + ".tmp")
    with open(temp, "w") as file:
        file.write("".join(row + "\n" for row in rows))
        file.flush()
        os.fsync(file.fileno())
    os.replace(temp, path)


def add(path: Path, camera_id: str) -> bool:
    if camera_id in load(path):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    write(path, [*lines(path), camera_id])
    return True


def remove(path: Path, camera_id: str) -> bool:
    if camera_id not in load(path):
        return False
    write(path, [line for line in lines(path) if line.strip() != camera_id])
    return True
