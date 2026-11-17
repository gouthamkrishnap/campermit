import shutil


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
        (target / "bind").touch()
        (target / "unbind").touch()
        (interface / "driver").symlink_to(target)
    for node in nodes:
        (interface / "video4linux" / node).mkdir(parents=True)


def unbind(root, name):
    interface = root / "bus/usb/devices" / name
    (interface / "driver").unlink()
    shutil.rmtree(interface / "video4linux", ignore_errors=True)
