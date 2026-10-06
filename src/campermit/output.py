import json

from .models import Camera


SCHEMA_VERSION = 1


def camera_summary(camera: Camera) -> dict[str, str | None]:
    return {
        "id": camera.id,
        "name": camera.name,
        "state": camera.state.value,
    }


def cameras_json(cameras: list[Camera]) -> str:
    data = {
        "schema_version": SCHEMA_VERSION,
        "cameras": [camera_summary(camera) for camera in cameras],
    }

    return json.dumps(data, indent=2)


def cameras_list(cameras: list[Camera]) -> str:
    if not cameras:
        return "No cameras found."

    rows = [
        ("ID", "NAME", "STATE"),
        *[
            (
                camera.id,
                camera.name or "-",
                camera.state.value,
            )
            for camera in cameras
        ],
    ]

    widths = [
        max(len(row[index]) for row in rows)
        for index in range(3)
    ]

    return "\n".join(
        "  ".join(
            value.ljust(width)
            for value, width in zip(row, widths)
        ).rstrip()
        for row in rows
    )


def camera_status(camera: Camera) -> str:
    return camera.state.value


def camera_status_json(camera: Camera) -> str:
    data = {
        "schema_version": SCHEMA_VERSION,
        **camera_summary(camera),
    }

    return json.dumps(data, indent=2)