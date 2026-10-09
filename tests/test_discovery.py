from pathlib import Path

from campermit.discovery import discover_cameras
from campermit.sysfs import Sysfs


def create_usb_device(
    root: Path,
    bus_path: str,
    *,
    vid: str = "0408",
    pid: str = "5482",
    name: str = "Test Camera",
    control_interfaces: int = 1,
    bound: bool = True,
) -> None:
    devices_root = root / "bus" / "usb" / "devices"
    device = devices_root / bus_path
    device.mkdir(parents=True)

    (device / "idVendor").write_text(f"{vid}\n")
    (device / "idProduct").write_text(f"{pid}\n")
    (device / "product").write_text(f"{name}\n")
    (device / "manufacturer").write_text("Test Vendor\n")
    (device / "serial").write_text(f"SERIAL-{bus_path}\n")

    for index in range(control_interfaces):
        interface_name = f"{bus_path}:1.{index}"

        # Physical interface directory, inside the USB device.
        interface = device / interface_name
        interface.mkdir()

        (interface / "bInterfaceClass").write_text("0e\n")
        (interface / "bInterfaceSubClass").write_text("01\n")

        # Sysfs also exposes the interface through a sibling symlink.
        interface_alias = devices_root / interface_name
        interface_alias.symlink_to(interface)

        if bound:
            driver = (
                root
                / "bus"
                / "usb"
                / "drivers"
                / "uvcvideo"
            )
            driver.mkdir(parents=True, exist_ok=True)
            (interface / "driver").symlink_to(driver)


def create_non_uvc_device(root: Path, bus_path: str) -> None:
    devices_root = root / "bus" / "usb" / "devices"
    device = devices_root / bus_path
    device.mkdir(parents=True)

    (device / "idVendor").write_text("1234\n")
    (device / "idProduct").write_text("5678\n")
    (device / "product").write_text("USB Device\n")

    interface_name = f"{bus_path}:1.0"
    interface = device / interface_name
    interface.mkdir()

    (interface / "bInterfaceClass").write_text("03\n")
    (interface / "bInterfaceSubClass").write_text("01\n")

    (devices_root / interface_name).symlink_to(interface)


def test_discovery_excludes_non_uvc_usb_devices(
    tmp_path: Path,
) -> None:
    create_non_uvc_device(tmp_path, "1-2")

    cameras = discover_cameras(Sysfs(tmp_path))

    assert cameras == []


def test_discovery_excludes_devices_with_multiple_control_interfaces(
    tmp_path: Path,
) -> None:
    create_usb_device(
        tmp_path,
        "3-6",
        control_interfaces=2,
    )

    cameras = discover_cameras(Sysfs(tmp_path))

    assert cameras == []


def test_discovery_assigns_deterministic_ids(
    tmp_path: Path,
) -> None:
    create_usb_device(tmp_path, "4-2", name="Camera B")
    create_usb_device(tmp_path, "3-6", name="Camera A")

    cameras = discover_cameras(Sysfs(tmp_path))

    assert [camera.bus_path for camera in cameras] == [
        "3-6",
        "4-2",
    ]
    assert [camera.id for camera in cameras] == ["1", "2"]
    assert [camera.name for camera in cameras] == [
        "Camera A",
        "Camera B",
    ]


def test_discovery_finds_unbound_camera(
    tmp_path: Path,
) -> None:
    create_usb_device(
        tmp_path,
        "3-6",
        bound=False,
    )

    cameras = discover_cameras(Sysfs(tmp_path))

    assert len(cameras) == 1
    assert cameras[0].id == "1"
    assert cameras[0].state.value == "disabled"
    assert cameras[0].functions[0].driver is None