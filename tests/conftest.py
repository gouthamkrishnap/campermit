import pytest
from fakesys import add_device, add_interface


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
