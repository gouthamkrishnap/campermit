from campermit import cli
from campermit.linux.uvc import Outcome, State
from campermit.models import Camera
from campermit.service import OperationResult


def make_camera() -> Camera:
    return Camera(
        id="1",
        bus_path="3-6",
        vid="0408",
        pid="5482",
        name="HP Wide Vision HD Camera",
    )


def test_enable_command(
    monkeypatch,
    capsys,
) -> None:
    camera = make_camera()

    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: [camera],
    )

    monkeypatch.setattr(
        cli,
        "enable",
        lambda camera, sysfs: OperationResult(
            outcome=Outcome.CHANGED,
            state=State.BOUND,
        ),
    )

    monkeypatch.setattr(
        cli,
        "Sysfs",
        lambda: object(),
    )

    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "enable", "1"],
    )

    cli.main()

    assert capsys.readouterr().out == "Camera 1 enabled.\n"


def test_disable_command(
    monkeypatch,
    capsys,
) -> None:
    camera = make_camera()

    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: [camera],
    )

    monkeypatch.setattr(
        cli,
        "disable",
        lambda camera, sysfs: OperationResult(
            outcome=Outcome.CHANGED,
            state=State.UNBOUND,
        ),
    )

    monkeypatch.setattr(
        cli,
        "Sysfs",
        lambda: object(),
    )

    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "disable", "1"],
    )

    cli.main()

    assert capsys.readouterr().out == "Camera 1 disabled.\n"


def test_toggle_command(
    monkeypatch,
    capsys,
) -> None:
    camera = make_camera()

    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: [camera],
    )

    monkeypatch.setattr(
        cli,
        "toggle",
        lambda camera, sysfs: OperationResult(
            outcome=Outcome.CHANGED,
            state=State.UNBOUND,
        ),
    )

    monkeypatch.setattr(
        cli,
        "Sysfs",
        lambda: object(),
    )

    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "toggle", "1"],
    )

    cli.main()

    assert capsys.readouterr().out == "Camera 1 disabled.\n"


def test_enable_json(
    monkeypatch,
    capsys,
) -> None:
    camera = make_camera()

    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: [camera],
    )

    monkeypatch.setattr(
        cli,
        "enable",
        lambda camera, sysfs: OperationResult(
            outcome=Outcome.CHANGED,
            state=State.BOUND,
        ),
    )

    monkeypatch.setattr(
        cli,
        "Sysfs",
        lambda: object(),
    )

    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "enable", "1", "--json"],
    )

    cli.main()

    assert capsys.readouterr().out == (
        '{\n'
        '  "schema_version": 1,\n'
        '  "id": "1",\n'
        '  "outcome": "changed",\n'
        '  "state": "enabled"\n'
        '}\n'
    )


def test_disable_already(
    monkeypatch,
    capsys,
) -> None:
    camera = make_camera()

    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: [camera],
    )

    monkeypatch.setattr(
        cli,
        "disable",
        lambda camera, sysfs: OperationResult(
            outcome=Outcome.ALREADY,
            state=State.UNBOUND,
        ),
    )

    monkeypatch.setattr(
        cli,
        "Sysfs",
        lambda: object(),
    )

    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "disable", "1"],
    )

    cli.main()

    assert capsys.readouterr().out == (
        "Camera 1 already disabled.\n"
    )


def test_enable_unknown_camera(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: [],
    )

    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "enable", "1"],
    )

    try:
        cli.main()
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("Expected SystemExit")