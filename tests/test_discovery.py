from fakesys import add_device, add_interface

from campermit.discovery import discover


def test_finds_the_laptop_camera(sysfs):
    cameras = discover(sysfs)

    assert len(cameras) == 1
    camera = cameras[0]
    assert camera.id == "3-6:1.0"
    assert camera.name == "HP Wide Vision HD Camera"
    assert camera.usb_id == "0408:5482"
    assert camera.driver == "uvcvideo"
    assert camera.nodes == ["/dev/video0", "/dev/video1"]


def test_disabled_camera_is_still_found(sysfs):
    (sysfs / "bus/usb/devices/3-6:1.0/driver").unlink()

    [camera] = discover(sysfs)

    assert camera.driver is None


def test_two_cameras_have_independent_state(sysfs):
    add_device(sysfs, "1-2", "046d", "0825", "Logitech", "Webcam C270")
    add_interface(sysfs, "1-2:1.0", "0e", "01", "uvcvideo", nodes=("video2",))
    add_interface(sysfs, "1-2:1.1", "0e", "02", "uvcvideo")
    (sysfs / "bus/usb/devices/3-6:1.0/driver").unlink()

    cameras = {camera.id: camera for camera in discover(sysfs)}

    assert cameras["1-2:1.0"].driver == "uvcvideo"
    assert cameras["3-6:1.0"].driver is None


def test_cameras_are_sorted_by_port_number(sysfs):
    add_device(sysfs, "3-10", "046d", "0825", "Logitech", "Webcam C270")
    add_interface(sysfs, "3-10:1.0", "0e", "01", "uvcvideo")
    add_device(sysfs, "1-2.3", "1bcf", "2c99", "Sunplus", "USB Camera")
    add_interface(sysfs, "1-2.3:1.0", "0e", "01", "uvcvideo")

    ids = [camera.id for camera in discover(sysfs)]

    assert ids == ["1-2.3:1.0", "3-6:1.0", "3-10:1.0"]
