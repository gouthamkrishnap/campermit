import pytest

from campermit import uvc


def test_write_does_not_create_missing_files(tmp_path):
    target = tmp_path / "unbind"

    with pytest.raises(FileNotFoundError):
        uvc.write(target, "3-6:1.0")

    assert not target.exists()


def test_write_sends_the_text_with_a_newline(tmp_path):
    target = tmp_path / "unbind"
    target.touch()

    uvc.write(target, "3-6:1.0")

    assert target.read_text() == "3-6:1.0\n"