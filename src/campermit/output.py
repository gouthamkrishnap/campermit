import json

from .linux.uvc import Outcome, State
from .models import Camera
from .service import OperationResult


SCHEMA_VERSION = 1


def camera_summary(camera: Camera) -> dict[str, str | None]:
    return {
        "id": camera.id,
        "name": camera.name,
        "state": camera.state.value,
    }


def camera_details(camera: Camera) -> dict:
    return {
        "id": camera.id,
        "name": camera.name,
        "bus_path": camera.bus_path,
        "vid": camera.vid,
        "pid": camera.pid,
        "serial": camera.serial,
        "vendor": camera.vendor,
        "product": camera.product,
        "removable": camera.removable,
        "state": camera.state.value,
        "functions": [
            {
                "control_interface": function.control_interface,
                "streaming_interfaces": function.streaming_interfaces,
                "driver": function.driver,
                "bound": function.bound,
                "video_nodes": function.video_nodes,
            }
            for function in camera.functions
        ],
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


def camera_info(camera: Camera) -> str:
    lines = [
        f"ID: {camera.id}",
        f"Name: {camera.name or '-'}",
        f"Bus path: {camera.bus_path}",
        f"VID: {camera.vid}",
        f"PID: {camera.pid}",
        f"Serial: {camera.serial or '-'}",
        f"Vendor: {camera.vendor or '-'}",
        f"Product: {camera.product or '-'}",
        f"Removable: {camera.removable}",
        f"State: {camera.state.value}",
    ]

    for index, function in enumerate(camera.functions, start=1):
        lines.extend(
            [
                "",
                f"UVC function {index}:",
                f"  Control interface: {function.control_interface}",
                (
                    "  Streaming interfaces: "
                    + ", ".join(function.streaming_interfaces)
                    if function.streaming_interfaces
                    else "  Streaming interfaces: -"
                ),
                f"  Driver: {function.driver or '-'}",
                f"  Bound: {function.bound}",
                (
                    "  Video nodes: "
                    + ", ".join(function.video_nodes)
                    if function.video_nodes
                    else "  Video nodes: -"
                ),
            ]
        )

    return "\n".join(lines)


def camera_info_json(camera: Camera) -> str:
    data = {
        "schema_version": SCHEMA_VERSION,
        **camera_details(camera),
    }

    return json.dumps(data, indent=2)


def cameras_info_json(cameras: list[Camera]) -> str:
    data = {
        "schema_version": SCHEMA_VERSION,
        "cameras": [camera_details(camera) for camera in cameras],
    }

    return json.dumps(data, indent=2)


def operation_result(
    camera: Camera,
    result: OperationResult,
) -> str:
    state = (
        "enabled"
        if result.state is State.BOUND
        else "disabled"
    )

    if result.outcome is Outcome.ALREADY:
        return f"Camera {camera.id} already {state}."

    return f"Camera {camera.id} {state}."


def operation_result_json(
    camera: Camera,
    result: OperationResult,
) -> str:
    data = {
        "schema_version": SCHEMA_VERSION,
        "id": camera.id,
        "outcome": result.outcome.value,
        "state": (
            "enabled"
            if result.state is State.BOUND
            else "disabled"
        ),
    }

    return json.dumps(data, indent=2)