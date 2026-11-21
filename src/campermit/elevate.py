import os
import stat
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

# The copy the polkit policy is written for. pkexec only gets this path.
INSTALLED = Path("/usr/bin/campermit")

# Where pkexec lives. /run/wrappers/bin is where NixOS keeps setuid programs.
PKEXEC_PATHS = (Path("/run/wrappers/bin/pkexec"), Path("/usr/bin/pkexec"))


def find_pkexec(candidates=PKEXEC_PATHS) -> str | None:
    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def safe_to_elevate(
    running: Path, installed: Path = INSTALLED, *, trusted_uid: int = 0
) -> bool:
    # Root runs the installed copy, so it must be the copy being run,
    # owned by root, and not writable by anyone else.
    try:
        if not os.path.samefile(running, installed):
            return False
        info = installed.stat()
    except OSError:
        return False

    return info.st_uid == trusted_uid and not info.st_mode & (
        stat.S_IWGRP | stat.S_IWOTH
    )


def command(pkexec: str, args: list[str], installed: Path = INSTALLED) -> list[str]:
    return [pkexec, str(installed), *args]


def run_elevated(cmd: list[str], run: Callable = subprocess.run) -> int:
    code = run(cmd).returncode

    # pkexec prints its own message when the prompt is dismissed (126).
    # 127 means it could not ask at all, usually because no agent is running.
    if code == 127:
        print(
            "campermit: could not ask for a password. Is a polkit agent "
            "running? You can also run this command with sudo.",
            file=sys.stderr,
        )

    return code


def ask_for_root(
    args: list[str],
    *,
    running: Path | None = None,
    installed: Path = INSTALLED,
    candidates=PKEXEC_PATHS,
    trusted_uid: int = 0,
    run: Callable = subprocess.run,
) -> int:
    if running is None:
        running = Path(sys.argv[0])

    if not safe_to_elevate(running, installed, trusted_uid=trusted_uid):
        print(
            f"campermit: this needs root. The password prompt only works for "
            f"the installed {installed}, so run this copy with sudo.",
            file=sys.stderr,
        )
        return 1

    pkexec = find_pkexec(candidates)

    if pkexec is None:
        print(
            "campermit: this needs root, and pkexec was not found. "
            "Install polkit or run it with sudo.",
            file=sys.stderr,
        )
        return 1

    return run_elevated(command(pkexec, args, installed), run)
