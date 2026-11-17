from fakesys import add_device, add_interface, unbind

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
    unbind(sysfs, "3-6:1.0")

    [camera] = discover(sysfs)

    assert camera.driver is None


def test_two_cameras_have_independent_state(sysfs):
    add_device(sysfs, "1-2", "046d", "0825", "Logitech", "Webcam C270")
    add_interface(sysfs, "1-2:1.0", "0e", "01", "uvcvideo", nodes=("video2",))
    add_interface(sysfs, "1-2:1.1", "0e", "02", "uvcvideo")
    unbind(sysfs, "3-6:1.0")

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


def test_camera_without_a_product_name_still_listed(sysfs):
    (sysfs / "bus/usb/devices/3-6/product").unlink()

    [camera] = discover(sysfs)

    assert camera.name == "USB camera 0408:5482"


def test_interface_that_disappeared_is_skipped(sysfs):
    (sysfs / "bus/usb/devices/3-8:1.0").mkdir()

    cameras = discover(sysfs)

    assert [camera.id for camera in cameras] == ["3-6:1.0"]


def test_one_usb_device_with_two_cameras_lists_both(sysfs):
    add_device(sysfs, "2-1", "0bda", "5830", "Realtek", "Dual Camera")
    add_interface(sysfs, "2-1:1.0", "0e", "01", "uvcvideo", nodes=("video4",))
    add_interface(sysfs, "2-1:1.1", "0e", "02", "uvcvideo")
    add_interface(sysfs, "2-1:1.2", "0e", "01", "uvcvideo", nodes=("video6",))
    add_interface(sysfs, "2-1:1.3", "0e", "02", "uvcvideo")
    unbind(sysfs, "2-1:1.2")

    cameras = {camera.id: camera for camera in discover(sysfs)}

    assert cameras["2-1:1.0"].driver == "uvcvideo"
    assert cameras["2-1:1.0"].nodes == ["/dev/video4"]
    assert cameras["2-1:1.2"].driver is None
    assert cameras["2-1:1.2"].nodes == []


def test_control_interface_without_streaming_is_still_listed(sysfs):
    add_device(sysfs, "2-2", "0bda", "5831", "Realtek", "Odd Camera")
    add_interface(sysfs, "2-2:1.0", "0e", "01", "uvcvideo")

    assert "2-2:1.0" in [camera.id for camera in discover(sysfs)]
