from .models import Camera


def select_camera(
    cameras: list[Camera],
    selector: str,
    *,
    name: bool = False,
) -> Camera:
    if name:
        matches = [
            camera
            for camera in cameras
            if camera.name == selector
        ]
    else:
        normalized_selector = selector.lower()

        matches = [
            camera
            for camera in cameras
            if (
                camera.id == selector
                or camera.bus_path == selector
                or f"{camera.vid}:{camera.pid}".lower()
                == normalized_selector
            )
        ]

    if not matches:
        raise ValueError(f"No camera matches '{selector}'.")

    if len(matches) > 1:
        raise ValueError(f"Camera selector '{selector}' is ambiguous.")

    return matches[0]