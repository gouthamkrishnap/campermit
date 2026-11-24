import fcntl
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import NamedTuple

from campermit.discovery import Camera

DEFAULT_PATH = Path("/etc/campermit/disabled")


def port_of(camera_id: str) -> str:
    return camera_id.partition("-")[2]


class Entry(NamedTuple):
    id: str
    usb_id: str | None = None
    controller: str | None = None

    def is_at(self, camera: Camera) -> bool:
        if self.controller is None:
            return self.id == camera.id
        same_port = port_of(self.id) == port_of(camera.id)
        return same_port and self.controller == camera.controller

    def matches(self, camera: Camera) -> bool:
        return self.is_at(camera) and self.usb_id in (None, camera.usb_id)

    def line(self) -> str:
        return " ".join(field for field in self if field)


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


def listed(path: Path, camera: Camera) -> bool:
    return any(entry.matches(camera) for entry in entries(path))


def is_for(line: str, camera: Camera) -> bool:
    entry = parse(line)
    return entry is not None and entry.matches(camera)


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


def add(path: Path, camera: Camera) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = Entry(camera.id, camera.usb_id, camera.controller)
    with locked(path.parent):
        if listed(path, camera):
            return False
        write(path, [*lines(path), entry.line()])
        return True


def remove(path: Path, camera: Camera) -> bool:
    if not listed(path, camera):
        return False
    with locked(path.parent):
        if not listed(path, camera):
            return False
        write(path, [line for line in lines(path) if not is_for(line, camera)])
        return True


def forget(path: Path, camera_id: str, cameras: list[Camera]) -> list[Entry]:
    def stale(entry: Entry) -> bool:
        return entry.id == camera_id and not any(
            entry.matches(camera) for camera in cameras
        )

    if not any(stale(entry) for entry in entries(path)):
        return []
    with locked(path.parent):
        gone = [entry for entry in entries(path) if stale(entry)]
        if not gone:
            return []
        kept = [
            line
            for line in lines(path)
            if (entry := parse(line)) is None or not stale(entry)
        ]
        write(path, kept)
        return gone
