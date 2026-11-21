import os
import subprocess
from pathlib import Path

from campermit import elevate


def make_installed(tmp_path, mode=0o755):
    installed = tmp_path / "campermit"
    installed.write_text("#!/bin/sh\n")
    installed.chmod(mode)
    return installed


def test_the_command_starts_with_pkexec_and_the_installed_path():
    command = elevate.command(
        "/usr/bin/pkexec", ["disable", "3-6", "--persist"], Path("/usr/bin/campermit")
    )

    assert command == [
        "/usr/bin/pkexec",
        "/usr/bin/campermit",
        "disable",
        "3-6",
        "--persist",
    ]


def test_find_pkexec_returns_the_first_one_that_exists(tmp_path):
    missing = tmp_path / "missing" / "pkexec"
    first = tmp_path / "first" / "pkexec"
    second = tmp_path / "second" / "pkexec"
    for path in (first, second):
        path.parent.mkdir()
        path.write_text("")

    assert elevate.find_pkexec([missing, first, second]) == str(first)


def test_find_pkexec_returns_none_when_there_is_none(tmp_path):
    assert elevate.find_pkexec([tmp_path / "nope" / "pkexec"]) is None


def test_the_installed_copy_is_safe_to_elevate(tmp_path):
    installed = make_installed(tmp_path)

    assert elevate.safe_to_elevate(installed, installed, trusted_uid=os.getuid())


def test_a_symlink_to_the_installed_copy_is_safe(tmp_path):
    installed = make_installed(tmp_path)
    link = tmp_path / "link"
    link.symlink_to(installed)

    assert elevate.safe_to_elevate(link, installed, trusted_uid=os.getuid())


def test_a_different_copy_is_not_safe(tmp_path):
    installed = make_installed(tmp_path)
    other = tmp_path / "other"
    other.write_text("#!/bin/sh\n")

    assert not elevate.safe_to_elevate(other, installed, trusted_uid=os.getuid())


def test_a_copy_owned_by_someone_else_is_not_safe(tmp_path):
    installed = make_installed(tmp_path)

    assert not elevate.safe_to_elevate(
        installed, installed, trusted_uid=os.getuid() + 1
    )


def test_a_copy_others_can_write_to_is_not_safe(tmp_path):
    for mode in (0o775, 0o757):
        installed = make_installed(tmp_path, mode)

        assert not elevate.safe_to_elevate(
            installed, installed, trusted_uid=os.getuid()
        )


def test_a_missing_installed_copy_is_not_safe(tmp_path):
    running = make_installed(tmp_path)

    assert not elevate.safe_to_elevate(
        running, tmp_path / "gone", trusted_uid=os.getuid()
    )


def fake_run(code, seen):
    def run(command):
        seen.append(command)
        return subprocess.CompletedProcess(command, code)

    return run


def test_run_elevated_runs_the_command_and_returns_its_exit_code(capsys):
    seen = []

    code = elevate.run_elevated(["pkexec", "x"], fake_run(0, seen))

    assert code == 0
    assert seen == [["pkexec", "x"]]
    assert capsys.readouterr().err == ""


def test_a_dismissed_prompt_adds_no_message_of_its_own(capsys):
    code = elevate.run_elevated(["pkexec", "x"], fake_run(126, []))

    assert code == 126
    assert capsys.readouterr().err == ""


def test_no_authentication_agent_suggests_sudo(capsys):
    code = elevate.run_elevated(["pkexec", "x"], fake_run(127, []))

    assert code == 127
    assert "sudo" in capsys.readouterr().err


def test_ask_for_root_runs_pkexec_with_the_installed_copy(tmp_path):
    installed = make_installed(tmp_path)
    pkexec = tmp_path / "pkexec"
    pkexec.write_text("")
    seen = []

    code = elevate.ask_for_root(
        ["disable", "3-6:1.0"],
        running=installed,
        installed=installed,
        candidates=[pkexec],
        trusted_uid=os.getuid(),
        run=fake_run(0, seen),
    )

    assert code == 0
    assert seen == [[str(pkexec), str(installed), "disable", "3-6:1.0"]]


def test_ask_for_root_passes_on_what_pkexec_returns(tmp_path):
    installed = make_installed(tmp_path)
    pkexec = tmp_path / "pkexec"
    pkexec.write_text("")

    code = elevate.ask_for_root(
        ["enable", "3-6:1.0"],
        running=installed,
        installed=installed,
        candidates=[pkexec],
        trusted_uid=os.getuid(),
        run=fake_run(126, []),
    )

    assert code == 126


def test_ask_for_root_refuses_a_copy_that_is_not_the_installed_one(tmp_path, capsys):
    installed = make_installed(tmp_path)
    other = tmp_path / "other"
    other.write_text("#!/bin/sh\n")
    seen = []

    code = elevate.ask_for_root(
        ["disable", "3-6:1.0"],
        running=other,
        installed=installed,
        candidates=[],
        trusted_uid=os.getuid(),
        run=fake_run(0, seen),
    )

    assert code == 1
    assert seen == []
    assert "sudo" in capsys.readouterr().err


def test_ask_for_root_says_so_when_pkexec_is_missing(tmp_path, capsys):
    installed = make_installed(tmp_path)
    seen = []

    code = elevate.ask_for_root(
        ["disable", "3-6:1.0"],
        running=installed,
        installed=installed,
        candidates=[tmp_path / "nope"],
        trusted_uid=os.getuid(),
        run=fake_run(0, seen),
    )

    error = capsys.readouterr().err
    assert code == 1
    assert seen == []
    assert "pkexec" in error
    assert "sudo" in error
