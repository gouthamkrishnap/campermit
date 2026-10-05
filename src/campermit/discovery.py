from pathlib import Path

from .models import Camera, UvcFunction
from .sysfs import Sysfs


USB_DEVICE_ROOT = ("bus", "usb", "devices")

UVC_CLASS = "0e"
UVC_VC_SUBCLASS = "01"
UVC_VS_SUBCLASS = "02"
UVC_DRIVER = "uvcvideo"


def discover_usb_devices(sysfs: Sysfs) -> list[Path]:
    root = sysfs.path(*USB_DEVICE_ROOT)

    return sorted(
        entry
        for entry in root.iterdir()
        if entry.is_dir()
        and (entry / "idVendor").is_file()
        and (entry / "idProduct").is_file()
    )


def discover_uvc_interfaces(
    sysfs: Sysfs,
    device: Path,
) -> tuple[list[str], list[str]]:
    control_interfaces = []
    streaming_interfaces = []

    for interface in sysfs.children(
        *USB_DEVICE_ROOT,
        device.name,
    ):
        class_path = interface / "bInterfaceClass"
        subclass_path = interface / "bInterfaceSubClass"

        if not class_path.is_file() or not subclass_path.is_file():
            continue

        interface_class = class_path.read_text().strip()
        interface_subclass = subclass_path.read_text().strip()

        if interface_class != UVC_CLASS:
            continue

        if interface_subclass == UVC_VC_SUBCLASS:
            control_interfaces.append(interface.name)
        elif interface_subclass == UVC_VS_SUBCLASS:
            streaming_interfaces.append(interface.name)

    return control_interfaces, streaming_interfaces


def get_interface_driver(
    sysfs: Sysfs,
    interface: str,
) -> str | None:
    driver_path = sysfs.path(
        "bus",
        "usb",
        "devices",
        interface,
        "driver",
    )

    if not driver_path.is_symlink():
        return None

    return driver_path.resolve().name


def get_uvc_driver(
    sysfs: Sysfs,
    control_interface: str,
) -> str | None:
    return get_interface_driver(sysfs, control_interface)


def read_optional(
    sysfs: Sysfs,
    device: Path,
    name: str,
) -> str | None:
    path = device / name

    if not path.is_file():
        return None

    value = path.read_text().strip()
    return value or None


def discover_camera(
    sysfs: Sysfs,
    device: Path,
) -> Camera | None:
    control_interfaces, streaming_interfaces = discover_uvc_interfaces(
        sysfs,
        device,
    )

    if len(control_interfaces) != 1:
        return None

    control_interface = control_interfaces[0]
    driver = get_uvc_driver(sysfs, control_interface)

    function = UvcFunction(
        control_interface=control_interface,
        streaming_interfaces=streaming_interfaces,
        driver=driver,
        bound=driver == UVC_DRIVER,
    )

    return Camera(
        id="",
        bus_path=device.name,
        vid=(device / "idVendor").read_text().strip(),
        pid=(device / "idProduct").read_text().strip(),
        serial=read_optional(sysfs, device, "serial"),
        vendor=read_optional(sysfs, device, "manufacturer"),
        product=read_optional(sysfs, device, "product"),
        functions=[function],
    )


def discover_cameras(sysfs: Sysfs) -> list[Camera]:
    cameras = []

    for device in discover_usb_devices(sysfs):
        camera = discover_camera(sysfs, device)

        if camera is not None:
            cameras.append(camera)

    cameras.sort(key=lambda camera: camera.bus_path)

    for index, camera in enumerate(cameras, start=1):
        camera.id = str(index)

    return cameras