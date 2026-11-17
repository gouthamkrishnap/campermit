import pytest


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n")


def add_device(root, name, vendor, product, manufacturer, product_name):
    device = root / "bus/usb/devices" / name
    write(device / "idVendor", vendor)
    write(device / "idProduct", product)
    write(device / "manufacturer", manufacturer)
    write(device / "product", product_name)


def add_interface(root, name, klass, subclass, driver=None, nodes=()):
    interface = root / "bus/usb/devices" / name
    write(interface / "bInterfaceClass", klass)
    write(interface / "bInterfaceSubClass", subclass)
    if driver:
        target = root / "bus/usb/drivers" / driver
        target.mkdir(parents=True, exist_ok=True)
        (interface / "driver").symlink_to(target)
    for node in nodes:
        (interface / "video4linux" / node).mkdir(parents=True)


@pytest.fixture
def sysfs(tmp_path):
    add_interface(tmp_path, "1-0:1.0", "09", "00", "hub")

    add_device(tmp_path, "3-6", "0408", "5482", " Quanta", "HP Wide Vision HD Camera")
    add_interface(
        tmp_path, "3-6:1.0", "0e", "01", "uvcvideo", nodes=("video0", "video1")
    )
    add_interface(tmp_path, "3-6:1.1", "0e", "02", "uvcvideo")
    add_interface(tmp_path, "3-6:1.2", "fe", "01")

    add_device(tmp_path, "3-7", "0bda", "b86a", "Realtek", "Bluetooth Radio")
    add_interface(tmp_path, "3-7:1.0", "e0", "01", "btusb")
    add_interface(tmp_path, "3-7:1.1", "e0", "01", "btusb")

    return tmp_path
