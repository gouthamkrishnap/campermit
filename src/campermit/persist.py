import fcntl
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import NamedTuple

DEFAULT_PATH = Path("/etc/campermit/disabled")


class Entry(NamedTuple):
    id: str
    usb_id: str | None = None
    controller: str | None = None


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


def parse(line: str) -> Entry | None:
    fields = line.split("#")[0].split()
    return Entry(*fields[:3]) if fields else None


def entries(path: Path) -> list[Entry]:
    return [entry for line in lines(path) if (entry := parse(line))]


def load(path: Path) -> list[str]:
    return [entry.id for entry in entries(path)]


def is_for(line: str, camera_id: str) -> bool:
    entry = parse(line)
    return entry is not None and entry.id == camera_id


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
        write(path, [line for line in lines(path) if not is_for(line, camera_id)])
        return True
