from campermit import cli
from campermit.linux.uvc import Outcome, State
from campermit.models import Camera
from campermit.service import (
    BatchOperationResult,
    OperationResult,
)


def make_camera() -> Camera:
    return Camera(
        id="1",
        bus_path="3-6",
        vid="0408",
        pid="5482",
        name="HP Wide Vision HD Camera",
    )


def test_enable_command(monkeypatch, capsys) -> None:
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

    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "enable", "1"],
    )

    cli.main()

    assert capsys.readouterr().out == "Camera 1 enabled.\n"


def test_disable_command(monkeypatch, capsys) -> None:
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

    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "disable", "1"],
    )

    cli.main()

    assert capsys.readouterr().out == "Camera 1 disabled.\n"


def test_toggle_command(monkeypatch, capsys) -> None:
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

    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "toggle", "1"],
    )

    cli.main()

    assert capsys.readouterr().out == "Camera 1 disabled.\n"


def test_enable_json(monkeypatch, capsys) -> None:
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

    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "enable", "1", "--json"],
    )

    cli.main()

    assert capsys.readouterr().out == (
        "{\n"
        '  "schema_version": 1,\n'
        '  "id": "1",\n'
        '  "outcome": "changed",\n'
        '  "state": "enabled"\n'
        "}\n"
    )


def test_disable_already(monkeypatch, capsys) -> None:
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

    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "disable", "1"],
    )

    cli.main()

    assert capsys.readouterr().out == "Camera 1 already disabled.\n"


def test_enable_unknown_camera(monkeypatch) -> None:
    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: [],
    )

    monkeypatch.setattr(cli, "Sysfs", lambda: object())
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


def test_enable_all_command(monkeypatch, capsys) -> None:
    cameras = [
        make_camera(),
        Camera(
            id="2",
            bus_path="4-2",
            vid="1234",
            pid="5678",
            name="Second Camera",
        ),
    ]

    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: cameras,
    )

    monkeypatch.setattr(
        cli,
        "enable_all",
        lambda cameras, sysfs: [
            BatchOperationResult(
                camera_id="1",
                result=OperationResult(
                    outcome=Outcome.CHANGED,
                    state=State.BOUND,
                ),
            ),
            BatchOperationResult(
                camera_id="2",
                result=OperationResult(
                    outcome=Outcome.ALREADY,
                    state=State.BOUND,
                ),
            ),
        ],
    )

    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "enable", "--all"],
    )

    cli.main()

    assert capsys.readouterr().out == (
        "Camera 1 enabled.\n"
        "Camera 2 already enabled.\n"
    )


def test_disable_all_command(monkeypatch, capsys) -> None:
    cameras = [
        make_camera(),
        Camera(
            id="2",
            bus_path="4-2",
            vid="1234",
            pid="5678",
            name="Second Camera",
        ),
    ]

    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: cameras,
    )

    monkeypatch.setattr(
        cli,
        "disable_all",
        lambda cameras, sysfs: [
            BatchOperationResult(
                camera_id="1",
                result=OperationResult(
                    outcome=Outcome.CHANGED,
                    state=State.UNBOUND,
                ),
            ),
            BatchOperationResult(
                camera_id="2",
                result=OperationResult(
                    outcome=Outcome.ALREADY,
                    state=State.UNBOUND,
                ),
            ),
        ],
    )

    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "disable", "--all"],
    )

    cli.main()

    assert capsys.readouterr().out == (
        "Camera 1 disabled.\n"
        "Camera 2 already disabled.\n"
    )


def test_enable_all_json(monkeypatch, capsys) -> None:
    cameras = [
        make_camera(),
        Camera(
            id="2",
            bus_path="4-2",
            vid="1234",
            pid="5678",
            name="Second Camera",
        ),
    ]

    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: cameras,
    )

    monkeypatch.setattr(
        cli,
        "enable_all",
        lambda cameras, sysfs: [
            BatchOperationResult(
                camera_id="1",
                result=OperationResult(
                    outcome=Outcome.CHANGED,
                    state=State.BOUND,
                ),
            ),
            BatchOperationResult(
                camera_id="2",
                result=OperationResult(
                    outcome=Outcome.ALREADY,
                    state=State.BOUND,
                ),
            ),
        ],
    )

    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "enable", "--all", "--json"],
    )

    cli.main()

    assert capsys.readouterr().out == (
        "{\n"
        '  "schema_version": 1,\n'
        '  "operation": "enable",\n'
        '  "results": [\n'
        "    {\n"
        '      "id": "1",\n'
        '      "outcome": "changed",\n'
        '      "state": "enabled"\n'
        "    },\n"
        "    {\n"
        '      "id": "2",\n'
        '      "outcome": "already",\n'
        '      "state": "enabled"\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )


def test_disable_all_json(monkeypatch, capsys) -> None:
    cameras = [
        make_camera(),
        Camera(
            id="2",
            bus_path="4-2",
            vid="1234",
            pid="5678",
            name="Second Camera",
        ),
    ]

    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: cameras,
    )

    monkeypatch.setattr(
        cli,
        "disable_all",
        lambda cameras, sysfs: [
            BatchOperationResult(
                camera_id="1",
                result=OperationResult(
                    outcome=Outcome.CHANGED,
                    state=State.UNBOUND,
                ),
            ),
            BatchOperationResult(
                camera_id="2",
                result=OperationResult(
                    outcome=Outcome.ALREADY,
                    state=State.UNBOUND,
                ),
            ),
        ],
    )

    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "disable", "--all", "--json"],
    )

    cli.main()

    assert capsys.readouterr().out == (
        "{\n"
        '  "schema_version": 1,\n'
        '  "operation": "disable",\n'
        '  "results": [\n'
        "    {\n"
        '      "id": "1",\n'
        '      "outcome": "changed",\n'
        '      "state": "disabled"\n'
        "    },\n"
        "    {\n"
        '      "id": "2",\n'
        '      "outcome": "already",\n'
        '      "state": "disabled"\n'
        "    }\n"
        "  ]\n"
        "}\n"
    )


def test_toggle_json(monkeypatch, capsys) -> None:
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

    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "toggle", "1", "--json"],
    )

    cli.main()

    assert capsys.readouterr().out == (
        "{\n"
        '  "schema_version": 1,\n'
        '  "id": "1",\n'
        '  "outcome": "changed",\n'
        '  "state": "disabled"\n'
        "}\n"
    )


def test_enable_error(monkeypatch, capsys) -> None:
    from campermit.errors import PermissionDenied

    camera = make_camera()

    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: [camera],
    )

    def fail_enable(camera, sysfs):
        raise PermissionDenied("Permission denied.")

    monkeypatch.setattr(cli, "enable", fail_enable)
    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "enable", "1"],
    )

    try:
        cli.main()
    except SystemExit as error:
        assert error.code == 1
    else:
        raise AssertionError("Expected SystemExit")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == "campermit: Permission denied."


def test_enable_all_error_returns_nonzero(
    monkeypatch,
    capsys,
) -> None:
    from campermit.errors import PermissionDenied

    cameras = [
        make_camera(),
        Camera(
            id="2",
            bus_path="4-2",
            vid="1234",
            pid="5678",
            name="Second Camera",
        ),
    ]

    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: cameras,
    )

    monkeypatch.setattr(
        cli,
        "enable_all",
        lambda cameras, sysfs: [
            BatchOperationResult(
                camera_id="1",
                error=PermissionDenied("Permission denied."),
            ),
            BatchOperationResult(
                camera_id="2",
                result=OperationResult(
                    outcome=Outcome.CHANGED,
                    state=State.BOUND,
                ),
            ),
        ],
    )

    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "enable", "--all"],
    )

    try:
        cli.main()
    except SystemExit as error:
        assert error.code == 1
    else:
        raise AssertionError("Expected SystemExit")

    assert capsys.readouterr().out == (
        "Camera 1: Permission denied.\n"
        "Camera 2 enabled.\n"
    )


def test_disable_all_error_returns_nonzero(
    monkeypatch,
    capsys,
) -> None:
    from campermit.errors import PermissionDenied

    cameras = [
        make_camera(),
        Camera(
            id="2",
            bus_path="4-2",
            vid="1234",
            pid="5678",
            name="Second Camera",
        ),
    ]

    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: cameras,
    )

    monkeypatch.setattr(
        cli,
        "disable_all",
        lambda cameras, sysfs: [
            BatchOperationResult(
                camera_id="1",
                error=PermissionDenied("Permission denied."),
            ),
            BatchOperationResult(
                camera_id="2",
                result=OperationResult(
                    outcome=Outcome.CHANGED,
                    state=State.UNBOUND,
                ),
            ),
        ],
    )

    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "disable", "--all"],
    )

    try:
        cli.main()
    except SystemExit as error:
        assert error.code == 1
    else:
        raise AssertionError("Expected SystemExit")

    assert capsys.readouterr().out == (
        "Camera 1: Permission denied.\n"
        "Camera 2 disabled.\n"
    )


def test_enable_all_json_error_returns_nonzero(
    monkeypatch,
    capsys,
) -> None:
    import json

    from campermit.errors import PermissionDenied

    cameras = [
        make_camera(),
        Camera(
            id="2",
            bus_path="4-2",
            vid="1234",
            pid="5678",
            name="Second Camera",
        ),
    ]

    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: cameras,
    )

    monkeypatch.setattr(
        cli,
        "enable_all",
        lambda cameras, sysfs: [
            BatchOperationResult(
                camera_id="1",
                error=PermissionDenied("Permission denied."),
            ),
            BatchOperationResult(
                camera_id="2",
                result=OperationResult(
                    outcome=Outcome.CHANGED,
                    state=State.BOUND,
                ),
            ),
        ],
    )

    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "enable", "--all", "--json"],
    )

    try:
        cli.main()
    except SystemExit as error:
        assert error.code == 1
    else:
        raise AssertionError("Expected SystemExit")

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["schema_version"] == 1
    assert data["operation"] == "enable"
    assert data["results"] == [
        {
            "id": "1",
            "error": "Permission denied.",
        },
        {
            "id": "2",
            "outcome": "changed",
            "state": "enabled",
        },
    ]
    assert captured.err == ""


def test_disable_all_json_error_returns_nonzero(
    monkeypatch,
    capsys,
) -> None:
    import json

    from campermit.errors import PermissionDenied

    cameras = [
        make_camera(),
        Camera(
            id="2",
            bus_path="4-2",
            vid="1234",
            pid="5678",
            name="Second Camera",
        ),
    ]

    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: cameras,
    )

    monkeypatch.setattr(
        cli,
        "disable_all",
        lambda cameras, sysfs: [
            BatchOperationResult(
                camera_id="1",
                error=PermissionDenied("Permission denied."),
            ),
            BatchOperationResult(
                camera_id="2",
                result=OperationResult(
                    outcome=Outcome.CHANGED,
                    state=State.UNBOUND,
                ),
            ),
        ],
    )

    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "disable", "--all", "--json"],
    )

    try:
        cli.main()
    except SystemExit as error:
        assert error.code == 1
    else:
        raise AssertionError("Expected SystemExit")

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert data["schema_version"] == 1
    assert data["operation"] == "disable"
    assert data["results"] == [
        {
            "id": "1",
            "error": "Permission denied.",
        },
        {
            "id": "2",
            "outcome": "changed",
            "state": "disabled",
        },
    ]
    assert captured.err == ""


def test_enable_all_with_no_cameras(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: [],
    )

    def unexpected_enable_all(cameras, sysfs):
        raise AssertionError("enable_all should not be called")

    monkeypatch.setattr(
        cli,
        "enable_all",
        unexpected_enable_all,
    )
    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "enable", "--all"],
    )

    cli.main()

    assert capsys.readouterr().out == "No cameras found.\n"


def test_disable_all_with_no_cameras(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        cli,
        "discover_cameras",
        lambda sysfs: [],
    )

    def unexpected_disable_all(cameras, sysfs):
        raise AssertionError("disable_all should not be called")

    monkeypatch.setattr(
        cli,
        "disable_all",
        unexpected_disable_all,
    )
    monkeypatch.setattr(cli, "Sysfs", lambda: object())
    monkeypatch.setattr(
        "sys.argv",
        ["campermit", "disable", "--all"],
    )

    cli.main()

    assert capsys.readouterr().out == "No cameras found.\n"
