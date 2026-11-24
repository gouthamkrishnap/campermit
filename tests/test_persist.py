import os
import threading

import pytest

from campermit import persist
from campermit.discovery import Camera


def camera(
    camera_id="3-6:1.0",
    usb_id="0408:5482",
    controller: str | None = "0000:00:14.0",
):
    return Camera(camera_id, "Camera", usb_id, "uvcvideo", [], controller)


def test_a_missing_file_means_nothing_is_kept_disabled(tmp_path):
    assert persist.load(tmp_path / "disabled") == []


def test_load_skips_blank_lines_and_comments(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("# my cameras\n\n3-6:1.0\n  1-2:1.0  \n")

    assert persist.load(path) == ["3-6:1.0", "1-2:1.0"]


def test_entries_read_the_id_the_model_and_the_controller(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("3-6:1.0 0408:5482 0000:00:14.0\n")

    assert persist.entries(path) == [
        persist.Entry("3-6:1.0", "0408:5482", "0000:00:14.0")
    ]


def test_an_old_line_with_only_the_id_is_still_read(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("3-6:1.0\n")

    assert persist.entries(path) == [persist.Entry("3-6:1.0", None, None)]


def test_entries_ignore_extra_spaces_extra_fields_and_comments(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("# mine\n\n  3-6:1.0\t0408:5482   0000:00:14.0  SN123\n")

    assert persist.entries(path) == [
        persist.Entry("3-6:1.0", "0408:5482", "0000:00:14.0")
    ]


def test_a_comment_after_the_fields_is_ignored(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("3-6:1.0 0408:5482 0000:00:14.0  # laptop camera\n")

    assert persist.entries(path) == [
        persist.Entry("3-6:1.0", "0408:5482", "0000:00:14.0")
    ]


def test_load_gives_the_ids_of_new_and_old_lines(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("3-6:1.0 0408:5482 0000:00:14.0\n1-2:1.0\n")

    assert persist.load(path) == ["3-6:1.0", "1-2:1.0"]


def test_adding_a_camera_that_has_a_full_line_changes_nothing(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("3-6:1.0 0408:5482 0000:00:14.0\n")

    assert persist.add(path, camera()) is False
    assert path.read_text() == "3-6:1.0 0408:5482 0000:00:14.0\n"


def test_remove_finds_a_full_line_by_its_id(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("# kept\n3-6:1.0 0408:5482 0000:00:14.0\n1-2:1.0\n")

    assert persist.remove(path, camera()) is True
    assert path.read_text() == "# kept\n1-2:1.0\n"


def test_add_creates_the_file_and_its_folder(tmp_path):
    path = tmp_path / "campermit" / "disabled"

    assert persist.add(path, camera()) is True
    assert path.read_text() == "3-6:1.0 0408:5482 0000:00:14.0\n"


def test_adding_the_same_camera_twice_changes_nothing(tmp_path):
    path = tmp_path / "disabled"
    persist.add(path, camera())

    assert persist.add(path, camera()) is False
    assert path.read_text() == "3-6:1.0 0408:5482 0000:00:14.0\n"


def test_add_keeps_the_line_of_a_different_camera_in_the_same_place(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("3-6:1.0 1234:abcd 0000:00:14.0\n")

    assert persist.add(path, camera()) is True
    assert persist.entries(path) == [
        persist.Entry("3-6:1.0", "1234:abcd", "0000:00:14.0"),
        persist.Entry("3-6:1.0", "0408:5482", "0000:00:14.0"),
    ]


def test_add_without_a_controller_saves_just_the_id_and_the_model(tmp_path):
    path = tmp_path / "disabled"

    persist.add(path, camera(controller=None))

    assert path.read_text() == "3-6:1.0 0408:5482\n"


def test_remove_drops_only_that_camera(tmp_path):
    path = tmp_path / "disabled"
    persist.add(path, camera())
    persist.add(path, camera("1-2:1.0"))

    assert persist.remove(path, camera()) is True
    assert persist.load(path) == ["1-2:1.0"]


def test_remove_keeps_comments_and_other_lines(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("# kept\n3-6:1.0\n")

    persist.remove(path, camera())

    assert path.read_text() == "# kept\n"


def test_remove_finds_a_line_after_the_bus_number_changed(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("2-6:1.0 0408:5482 0000:00:14.0\n")

    assert persist.remove(path, camera("3-6:1.0")) is True
    assert persist.load(path) == []


def test_remove_keeps_the_line_of_a_different_camera_in_the_same_place(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("3-6:1.0 1234:abcd 0000:00:14.0\n")

    assert persist.remove(path, camera()) is False
    assert path.read_text() == "3-6:1.0 1234:abcd 0000:00:14.0\n"


def test_removing_a_camera_that_is_not_listed_does_nothing(tmp_path):
    path = tmp_path / "disabled"

    assert persist.remove(path, camera()) is False
    assert not path.exists()


def test_forget_removes_a_line_that_matches_no_camera(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("9-9:1.0 1234:abcd 0000:00:0d.0\n3-6:1.0 0408:5482 0000:00:14.0\n")

    gone = persist.forget(path, "9-9:1.0", [camera()])

    assert gone == [persist.Entry("9-9:1.0", "1234:abcd", "0000:00:0d.0")]
    assert path.read_text() == "3-6:1.0 0408:5482 0000:00:14.0\n"


def test_forget_keeps_a_line_that_matches_a_connected_camera(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("3-6:1.0 0408:5482 0000:00:14.0\n")

    assert persist.forget(path, "3-6:1.0", [camera()]) == []
    assert path.read_text() == "3-6:1.0 0408:5482 0000:00:14.0\n"


def test_forget_removes_only_the_stale_line_that_shares_an_id(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("3-6:1.0 1234:abcd 0000:00:14.0\n3-6:1.0 0408:5482 0000:00:14.0\n")

    persist.forget(path, "3-6:1.0", [camera()])

    assert path.read_text() == "3-6:1.0 0408:5482 0000:00:14.0\n"


def test_forget_keeps_comments_and_other_lines(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("# kept\n9-9:1.0 1234:abcd 0000:00:0d.0\n")

    persist.forget(path, "9-9:1.0", [])

    assert path.read_text() == "# kept\n"


def test_forgetting_with_no_file_does_nothing(tmp_path):
    path = tmp_path / "campermit" / "disabled"

    assert persist.forget(path, "9-9:1.0", []) == []
    assert not path.parent.exists()


def test_writing_leaves_no_temp_file_behind(tmp_path):
    path = tmp_path / "disabled"

    persist.add(path, camera())

    assert [item.name for item in tmp_path.iterdir()] == ["disabled"]


def test_a_failed_write_keeps_the_old_file(tmp_path, monkeypatch):
    path = tmp_path / "disabled"
    persist.add(path, camera())

    def fail(source, target):
        raise OSError("disk full")

    monkeypatch.setattr(persist.os, "replace", fail)

    with pytest.raises(OSError):
        persist.add(path, camera("1-2:1.0"))

    assert path.read_text() == "3-6:1.0 0408:5482 0000:00:14.0\n"


def test_a_failed_write_leaves_no_temp_file_behind(tmp_path, monkeypatch):
    path = tmp_path / "disabled"
    persist.add(path, camera())

    def fail(source, target):
        raise OSError("disk full")

    monkeypatch.setattr(persist.os, "replace", fail)

    with pytest.raises(OSError):
        persist.add(path, camera("1-2:1.0"))

    assert [item.name for item in tmp_path.iterdir()] == ["disabled"]


def test_two_writes_at_once_do_not_share_a_temp_file(tmp_path, monkeypatch):
    path = tmp_path / "disabled"
    real_replace = os.replace
    rival_has_run = []

    def replace_after_a_rival_write(source, target):
        if not rival_has_run:
            rival_has_run.append(True)
            persist.write(path, ["1-2:1.0"])
        real_replace(source, target)

    monkeypatch.setattr(persist.os, "replace", replace_after_a_rival_write)

    persist.write(path, ["3-6:1.0"])

    assert persist.load(path) == ["3-6:1.0"]


def test_the_list_stays_readable_by_everyone(tmp_path):
    path = tmp_path / "disabled"

    persist.add(path, camera())

    assert path.stat().st_mode & 0o777 == 0o644


def test_two_adds_at_once_keep_both_cameras(tmp_path, monkeypatch):
    path = tmp_path / "disabled"
    real_write = persist.write
    rival = threading.Thread(target=persist.add, args=(path, camera("1-2:1.0")))
    started = []

    def write_after_a_rival_starts(target, rows):
        if not started:
            started.append(True)
            rival.start()
            rival.join(timeout=0.2)
        real_write(target, rows)

    monkeypatch.setattr(persist, "write", write_after_a_rival_starts)

    persist.add(path, camera())
    rival.join()

    assert sorted(persist.load(path)) == ["1-2:1.0", "3-6:1.0"]


def test_two_removes_at_once_keep_the_other_cameras(tmp_path, monkeypatch):
    path = tmp_path / "disabled"
    path.write_text("3-6:1.0\n1-2:1.0\n2-1:1.0\n")
    real_write = persist.write
    rival = threading.Thread(target=persist.remove, args=(path, camera("1-2:1.0")))
    started = []

    def write_after_a_rival_starts(target, rows):
        if not started:
            started.append(True)
            rival.start()
            rival.join(timeout=0.2)
        real_write(target, rows)

    monkeypatch.setattr(persist, "write", write_after_a_rival_starts)

    persist.remove(path, camera())
    rival.join()

    assert persist.load(path) == ["2-1:1.0"]
