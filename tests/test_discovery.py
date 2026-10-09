from pathlib import Path

from campermit.discovery import discover_cameras
from campermit.models import CameraState
from campermit.sysfs import Sysfs


USB_ROOT = ("bus", "usb", "devices")
UVC_CLASS = "0e"
VC_SUBCLASS = "01"
VS_SUBCLASS = "02"


def add_usb_device(
    root: Path,
    bus_path: str,
    interfaces: list[tuple[str, str]],
) -> Path:
    devices = root.joinpath(*USB_ROOT)
    physical_device = root / "devices" / "usb3" / bus_path
    physical_device.mkdir(parents=True)

    (physical_device / "idVendor").write_text("0408\n")
    (physical_device / "idProduct").write_text("5482\n")
    (physical_device / "product").write_text("Test Camera\n")

    devices.mkdir(parents=True, exist_ok=True)
    (devices / bus_path).symlink_to(physical_device)

    for index, (interface_class, subclass) in enumerate(interfaces):
        interface_name = f"{bus_path}:1.{index}"
        physical_interface = physical_device / interface_name
        physical_interface.mkdir()

        (physical_interface / "bInterfaceClass").write_text(
            f"{interface_class}\n"
        )
        (physical_interface / "bInterfaceSubClass").write_text(
            f"{subclass}\n"
        )

        (devices / interface_name).symlink_to(physical_interface)

    return physical_device


def test_excludes_non_uvc_usb_devices(tmp_path: Path) -> None:
    add_usb_device(
        tmp_path,
        "3-6",
        [("03", "01")],
    )

    assert discover_cameras(Sysfs(tmp_path)) == []


def test_excludes_device_with_multiple_vc_interfaces(
    tmp_path: Path,
) -> None:
    add_usb_device(
        tmp_path,
        "3-6",
        [
            (UVC_CLASS, VC_SUBCLASS),
            (UVC_CLASS, VC_SUBCLASS),
            (UVC_CLASS, VS_SUBCLASS),
        ],
    )

    assert discover_cameras(Sysfs(tmp_path)) == []


def test_assigns_deterministic_ids_by_bus_path(
    tmp_path: Path,
) -> None:
    add_usb_device(
        tmp_path,
        "3-6",
        [
            (UVC_CLASS, VC_SUBCLASS),
            (UVC_CLASS, VS_SUBCLASS),
        ],
    )
    add_usb_device(
        tmp_path,
        "1-2",
        [
            (UVC_CLASS, VC_SUBCLASS),
            (UVC_CLASS, VS_SUBCLASS),
        ],
    )

    cameras = discover_cameras(Sysfs(tmp_path))

    assert [
        (camera.id, camera.bus_path) for camera in cameras
    ] == [
        ("1", "1-2"),
        ("2", "3-6"),
    ]


def test_discovers_unbound_camera(tmp_path: Path) -> None:
    add_usb_device(
        tmp_path,
        "3-6",
        [
            (UVC_CLASS, VC_SUBCLASS),
            (UVC_CLASS, VS_SUBCLASS),
        ],
    )

    cameras = discover_cameras(Sysfs(tmp_path))

    assert len(cameras) == 1
    assert cameras[0].state is CameraState.DISABLED
    assert cameras[0].functions[0].driver is None


def test_excludes_vc_only_device(tmp_path: Path) -> None:
    add_usb_device(
        tmp_path,
        "3-6",
        [(UVC_CLASS, VC_SUBCLASS)],
    )

    assert discover_cameras(Sysfs(tmp_path)) == []
