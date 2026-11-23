import fcntl
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DEFAULT_PATH = Path("/etc/campermit/disabled")


@contextmanager
def locked(folder: Path) -> Iterator[None]:
    descriptor = os.open(folder, os.O_RDONLY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def lines(path: Path) -> list[str]:
    try:
        return path.read_text().splitlines()
    except FileNotFoundError:
        return []


def load(path: Path) -> list[str]:
    ids = (line.strip() for line in lines(path))
    return [text for text in ids if text and not text.startswith("#")]


def write(path: Path, rows: list[str]) -> None:
    descriptor, temp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    try:
        with os.fdopen(descriptor, "w") as file:
            os.fchmod(file.fileno(), 0o644)
            file.write("".join(row + "\n" for row in rows))
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp, path)
    except BaseException:
        os.unlink(temp)
        raise


def add(path: Path, camera_id: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    with locked(path.parent):
        if camera_id in load(path):
            return False
        write(path, [*lines(path), camera_id])
        return True


def remove(path: Path, camera_id: str) -> bool:
    if camera_id not in load(path):
        return False
    with locked(path.parent):
        if camera_id not in load(path):
            return False
        write(path, [line for line in lines(path) if line.strip() != camera_id])
        return True
