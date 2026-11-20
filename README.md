# CamPermit

Enable and disable USB webcams on Linux from the command line.

campermit turns a camera off by unbinding it from the `uvcvideo` driver, which is
what you would do by hand through `/sys`. The camera stays plugged in, but nothing
can open it until you turn it back on. It only works with USB (UVC) cameras.

It is software. A physical shutter or a hardware kill switch is still the only
way to be sure.

```
$ campermit list
ID       NAME                      USB ID     STATE    NODES
3-6:1.0  HP Wide Vision HD Camera  0408:5482  enabled  /dev/video0 /dev/video1

$ sudo campermit disable 3-6
Disabled 3-6:1.0  HP Wide Vision HD Camera
```

The IDs in these examples come from the laptop campermit was tested on. Run `campermit list` to see yours.

## Install

### Arch Linux

Build and install the package from this repository. `makepkg` downloads the
release archive and checks it against a checksum:

```
git clone https://github.com/gouthamkrishnap/campermit.git
cd campermit/packaging/arch
makepkg -si
```

After that, `sudo campermit disable ID` works as it is, where ID comes from `campermit list`.

### Other distributions

You need Python 3.11 or newer.

```
git clone https://github.com/gouthamkrishnap/campermit.git
cd campermit
python -m venv .venv
.venv/bin/pip install .
```

Changing a camera needs root, and `sudo` does not see programs inside a virtual
environment. Give it the full path:

```
sudo .venv/bin/campermit disable 3-6
```

Listing cameras and reading their state works without root.

`--persist` also needs the udev rule. The Arch package installs it. On other
distributions, install it yourself, with the path to your `campermit` in it (shown
here for the virtual environment above):

```
sed "s|/usr/bin/campermit|$PWD/.venv/bin/campermit|" packaging/udev/99-campermit.rules | sudo tee /etc/udev/rules.d/99-campermit.rules
sudo udevadm control --reload
```

## Usage

```
campermit list                 show the cameras and whether they are on
campermit status CAMERA        print enabled, disabled, or which driver has it
campermit enable CAMERA        turn a camera on
campermit disable CAMERA       turn a camera off
campermit toggle CAMERA        flip it
campermit enable --all         do it for every camera
campermit disable --all
```

`CAMERA` can be any of these:

| You type | Meaning |
| --- | --- |
| `3-6:1.0` | the exact camera ID, as shown by `list` |
| `3-6` | a USB device, if it has only one camera |
| `0408:5482` | a vendor and product ID |
| `wide vision` | part of the camera's name, at least 3 characters, any letter case |

A name with several words needs quotes: `campermit disable "wide vision"`. One word is usually enough: `campermit disable wide`.

If a name matches more than one camera, campermit says which ones and does nothing.
Every change prints which camera it touched.

`--all` acts on every UVC video device it finds, including HDMI capture cards that
present themselves as cameras. `list` shows exactly what `--all` will act on. To be
selective, name the camera.

Asking for a state the camera is already in is not an error.

### Keeping a camera off

`disable` lasts until the next reboot. To keep a camera off, add `--persist`:

```
sudo campermit disable 3-6 --persist
```

This saves the camera's ID in `/etc/campermit/disabled`. A udev rule reads that file each time a camera appears, at boot or when you plug it in, and turns the camera off again. `enable` takes the camera out of the file, so it stays on. `disable --all --persist` does it for every camera `list` shows.

The rule runs `campermit restore ID`. You don't need to run it yourself.

### For scripts

`campermit list --json` prints the cameras as JSON:

```json
{
  "schema_version": 1,
  "cameras": [
    {
      "id": "3-6:1.0",
      "name": "HP Wide Vision HD Camera",
      "usb_id": "0408:5482",
      "state": "enabled",
      "driver": "uvcvideo",
      "nodes": ["/dev/video0", "/dev/video1"]
    }
  ]
}
```

`state` is `enabled`, `disabled`, or `other` (bound to a different driver, named in
`driver`). New fields may be added. `schema_version` changes only if a field is
renamed or removed.

Exit codes: `0` when the camera ended up as asked, `1` when something failed,
`2` for a usage mistake.

## What to expect

- A disabled camera stays disabled through suspend and resume.
- Without `--persist`, a disabled camera comes back on after a reboot. With it, the
  camera is turned off again as soon as its driver attaches, so it is on briefly at
  boot.
- Replugging an external camera has not been tested.
- Uninstalling campermit does not change any camera. To get one back right away,
  run `sudo campermit enable --all` before removing it, or reboot. If
  campermit is already gone, this does the same by hand (use your camera's ID):

  ```
  echo '3-6:1.0' | sudo tee /sys/bus/usb/drivers/uvcvideo/bind
  ```

## Limits

- USB cameras only. Many newer laptops have a built-in camera that is not USB
  (MIPI). campermit can't see or control those, and `list` says so.
- It has only been tested on one laptop with one camera: an HP Wide Vision HD
  Camera on kernel 7.3, CachyOS.
- A camera that another driver already holds is left alone and reported.

## Development

```
python -m venv .venv
.venv/bin/pip install -e . --group dev
.venv/bin/pytest
.venv/bin/ruff check
```

`--group` needs pip 25.1 or newer.

The tests run against a fake `/sys` tree, so they need no camera and no root.

## License

MIT. See [LICENSE](LICENSE).