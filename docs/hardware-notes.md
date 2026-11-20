# Hardware notes

Tested on the built-in HP Wide Vision HD Camera (Quanta, USB ID `0408:5482`).
Kernel 7.3.3-1-cachyos.

## Naming

The camera is `3-6` in `/sys/bus/usb/devices/` (bus 3, port 6). An interface adds
`:1.N`, where N is the interface number. The `Device` number from `lsusb` changes
and is not part of the name.

| Interface | Class | Subclass | Role | Driver |
| --- | --- | --- | --- | --- |
| `3-6:1.0` | `0e` | `01` | video control | `uvcvideo` |
| `3-6:1.1` | `0e` | `02` | video streaming | `uvcvideo` |
| `3-6:1.2` | `fe` | `01` | firmware update | none |

Class and subclass come from `bInterfaceClass` and `bInterfaceSubClass`. The
control interface is the one with class `0e` and subclass `01`.

## Findings

- The `video4linux/` and `media0/` folders are only under the control interface.
  `video0` and `video1` are both listed there, so no system-wide scan is needed.
- The kernel cuts the video node name to 31 characters, and both nodes get the
  same one, so the name can't tell them apart.
- Files in `/sys` end with a newline and can start with a space (`manufacturer`
  is ` Quanta`). Always strip them.
- A device with no driver has no `driver` link at all.
- `bind` and `unbind` live in `/sys/bus/usb/drivers/uvcvideo/` and are writable
  by root only.

## Unbind and bind

- Unbinding the control interface (`3-6:1.0`) also frees the streaming interface
  (`3-6:1.1`). Both lose the driver and `/dev/video0` and `/dev/video1` disappear.
- A disabled camera still shows up as class `0e`, just without a driver, so
  discovery has to go by class and not by driver.
- Writes finish before they return. The driver link is gone (or back) right
  after the command ends, so there is nothing to poll for.
- A disabled camera stayed disabled after a suspend and resume.
- After a reboot the camera is bound again, and `video0` and `video1` are back.
  Nothing was set to disable it at boot.
- After a bind, the nodes came back as `video0` and `video1`, with group `video`
  and an ACL (`crw-rw----+`) a few seconds later. Whether they are briefly
  `root root` right after the bind is not verified.

## udev

- A rule on `bind` for `3-6:1.0` fired once when the camera was enabled, and not
  when it was disabled.
- At boot the same rule fired for both `add` and `bind`, in the same second.
- A rule that unbinds the camera from `RUN+=` works, and the camera was still
  disabled after a reboot.
- With the rule installed, `campermit enable` left the camera on, because it
  takes the camera off the list before binding it.

## Errors

| Write | State | Error |
| --- | --- | --- |
| `bind` | already bound | `Device or resource busy` |
| `unbind` | already unbound | `No such device` |

So the tool must check the state first. If it still gets one of these errors, the
camera is already in the state we wanted.

## Not checked yet

- An app holding the camera open during unbind.
- Unplugging an external camera during a write.
- Two commands running at once.
- External USB cameras, or laptops with more than one camera.
- Which events fire when `uvcvideo` is loaded before udev starts.
