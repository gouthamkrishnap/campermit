import pytest
from fakesys import add_device, add_interface, unbind

from campermit.discovery import discover, find_camera


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


def test_find_camera_by_usb_id(sysfs):
    cameras = discover(sysfs)

    assert [c.id for c in find_camera(cameras, "0408:5482")] == ["3-6:1.0"]


def test_usb_id_match_ignores_letter_case(sysfs):
    add_device(sysfs, "2-1", "0bda", "5830", "Realtek", "Some Camera")
    add_interface(sysfs, "2-1:1.0", "0e", "01", "uvcvideo")

    found = find_camera(discover(sysfs), "0BDA:5830")

    assert [c.id for c in found] == ["2-1:1.0"]


def test_two_cameras_with_the_same_usb_id_both_match(sysfs):
    for port in ("1-2", "2-1"):
        add_device(sysfs, port, "046d", "0825", "Logitech", "Webcam C270")
        add_interface(sysfs, f"{port}:1.0", "0e", "01", "uvcvideo")

    found = find_camera(discover(sysfs), "046d:0825")

    assert [c.id for c in found] == ["1-2:1.0", "2-1:1.0"]


def test_unknown_usb_id_matches_nothing(sysfs):
    assert find_camera(discover(sysfs), "ffff:ffff") == []


@pytest.mark.parametrize("missing", ["idVendor", "idProduct"])
def test_camera_with_a_missing_usb_id_is_skipped(sysfs, missing):
    (sysfs / "bus/usb/devices/3-6" / missing).unlink()

    assert discover(sysfs) == []
