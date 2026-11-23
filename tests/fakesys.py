import shutil

DEFAULT_CONTROLLER = "0000:00:14.0"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n")


def add_device(
    root,
    name,
    vendor,
    product,
    manufacturer,
    product_name,
    controller=DEFAULT_CONTROLLER,
):
    bus = name.split("-")[0]
    device = root / "devices/pci0000:00" / controller / f"usb{bus}" / name
    write(device / "idVendor", vendor)
    write(device / "idProduct", product)
    write(device / "manufacturer", manufacturer)
    write(device / "product", product_name)
    link(root, name, device)


def add_interface(root, name, klass, subclass, driver=None, nodes=()):
    device = root / "bus/usb/devices" / name.split(":")[0]
    if device.exists():
        interface = device.resolve() / name
        link(root, name, interface)
    else:
        interface = root / "bus/usb/devices" / name
    write(interface / "bInterfaceClass", klass)
    write(interface / "bInterfaceSubClass", subclass)
    if driver:
        target = root / "bus/usb/drivers" / driver
        target.mkdir(parents=True, exist_ok=True)
        (target / "bind").touch()
        (target / "unbind").touch()
        (interface / "driver").symlink_to(target)
    for node in nodes:
        (interface / "video4linux" / node).mkdir(parents=True)


def link(root, name, target):
    folder = root / "bus/usb/devices"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).symlink_to(target)


def unbind(root, name):
    interface = root / "bus/usb/devices" / name
    (interface / "driver").unlink()
    shutil.rmtree(interface / "video4linux", ignore_errors=True)
