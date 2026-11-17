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
