from campermit import persist


def test_a_missing_file_means_nothing_is_kept_disabled(tmp_path):
    assert persist.load(tmp_path / "disabled") == []


def test_load_skips_blank_lines_and_comments(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("# my cameras\n\n3-6:1.0\n  1-2:1.0  \n")

    assert persist.load(path) == ["3-6:1.0", "1-2:1.0"]


def test_add_creates_the_file_and_its_folder(tmp_path):
    path = tmp_path / "campermit" / "disabled"

    assert persist.add(path, "3-6:1.0") is True
    assert path.read_text() == "3-6:1.0\n"


def test_adding_the_same_camera_twice_changes_nothing(tmp_path):
    path = tmp_path / "disabled"
    persist.add(path, "3-6:1.0")

    assert persist.add(path, "3-6:1.0") is False
    assert path.read_text() == "3-6:1.0\n"


def test_remove_drops_only_that_camera(tmp_path):
    path = tmp_path / "disabled"
    persist.add(path, "3-6:1.0")
    persist.add(path, "1-2:1.0")

    assert persist.remove(path, "3-6:1.0") is True
    assert persist.load(path) == ["1-2:1.0"]


def test_remove_keeps_comments_and_other_lines(tmp_path):
    path = tmp_path / "disabled"
    path.write_text("# kept\n3-6:1.0\n")

    persist.remove(path, "3-6:1.0")

    assert path.read_text() == "# kept\n"


def test_removing_a_camera_that_is_not_listed_does_nothing(tmp_path):
    path = tmp_path / "disabled"

    assert persist.remove(path, "3-6:1.0") is False
    assert not path.exists()
