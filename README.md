# CamPermit

Enable and disable USB webcams on Linux from the command line.

campermit turns a camera off by unbinding it from the `uvcvideo` driver, which is
what you would do by hand through `/sys`. The camera stays connected to the
system, but programs can no longer open it until you turn it back on. It can also
keep a camera off after a reboot. It only works with USB (UVC) cameras.

It is software. A physical shutter or a hardware kill switch is still the only
way to be sure.

```
$ campermit list
ID       NAME                      USB ID     STATE    NODES
3-6:1.0  HP Wide Vision HD Camera  0408:5482  enabled  /dev/video0 /dev/video1

$ campermit disable 3-6
Disabled 3-6:1.0  HP Wide Vision HD Camera
```

The IDs in these examples come from the laptop campermit was tested on. Run `campermit list` to see yours.

Changing a camera needs root. With the Arch package, campermit asks for your password in a dialog, so the examples here have no `sudo`. On any other install, put `sudo` in front of the commands that change a camera. [Passwords and sudo](#passwords-and-sudo) has the details.

campermit is early software, tested on one laptop with one camera. Arch Linux is the only distribution with a package for now.

## Install

### Arch Linux

```
git clone https://github.com/gouthamkrishnap/campermit.git
cd campermit/packaging/arch
makepkg -si
```

`makepkg` downloads the release named in the PKGBUILD, checks it against a checksum, and builds that. It does not build the files you just cloned. The package installs `campermit` in `/usr/bin`, the udev rule that `--persist` needs, and a polkit policy for the password dialog. polkit is optional. Most desktops have it, and without it you use `sudo` instead.

Then run `campermit list` to see your cameras.

### Other distributions

You need Python 3.11 or newer. Install campermit into a virtual environment that only root can change, and link it into `/usr/local/bin`:

```
git clone https://github.com/gouthamkrishnap/campermit.git
cd campermit
sudo python3 -m venv /opt/campermit
sudo /opt/campermit/bin/pip install .
sudo ln -s /opt/campermit/bin/campermit /usr/local/bin/campermit
```

Now `campermit list` works, and so does `sudo campermit disable 3-6`.

`--persist` also needs the udev rule, pointed at that copy:

```
sed "s|/usr/bin/campermit|/opt/campermit/bin/campermit|" packaging/udev/99-campermit.rules | sudo tee /etc/udev/rules.d/99-campermit.rules
sudo udevadm control --reload
```

The rule runs campermit as root every time a camera appears, which is why it has to point at a copy only root can change. A virtual environment in your home folder is not that: anything running as you could edit it, and then run as root.

These steps have not been tried with a real camera on a distribution other than Arch.

## Usage

Commands that change a camera need root, so outside the Arch package put `sudo` in front of them. See [Passwords and sudo](#passwords-and-sudo).

```
campermit list                       show the cameras, whether they are on, and which are kept off
campermit status CAMERA              print enabled, disabled, or which driver has it
campermit enable CAMERA              turn a camera on
campermit disable CAMERA             turn a camera off
campermit disable CAMERA --persist   turn it off and keep it off after a reboot
campermit toggle CAMERA              flip it
campermit enable --all               do it for every camera
campermit disable --all
campermit disable --all --persist
campermit forget ID                  drop a saved camera that is not connected
```

`CAMERA` can be any of these:

| You type | Meaning |
| --- | --- |
| `3-6:1.0` | the exact camera ID, as shown by `list` |
| `3-6` | a USB device, if it has only one camera |
| `0408:5482` | a vendor and product ID |
| `"wide vision"` | part of the camera's name, at least 3 characters, any letter case |

A name with several words needs quotes: `campermit disable "wide vision"`. One word is usually enough: `campermit disable wide`.

If a name matches more than one camera, campermit says which ones and does nothing. Every change prints which camera it touched. Asking for a state the camera is already in is not an error.

`--all` acts on every UVC video device it finds, including HDMI capture cards that
present themselves as cameras. `list` shows exactly what `--all` will act on. To be
selective, name the camera.

A disabled camera stays disabled through suspend and resume. After a reboot it comes back on, unless you used `--persist`. If a program is using the camera when you disable it, the program loses the camera, as if it had been unplugged.

## Passwords and sudo

`list` and `status` never need root. `enable`, `disable`, `toggle` and `forget` do. A command with nothing to change, like disabling a camera that is already off, doesn't ask at all.

There are two ways to give root:

| How campermit is installed | What to type |
| --- | --- |
| Arch package | `campermit disable 3-6`, and a password dialog appears. `sudo campermit disable 3-6` works too. |
| Anything else | `sudo campermit disable 3-6`. If campermit is only inside a virtual environment or was installed with pipx, `sudo` can't find it by name, so give the full path, for example `sudo .venv/bin/campermit disable 3-6`. |

The dialog comes from polkit. At the machine it wants your own password. In a session that isn't at the machine, such as over ssh, it wants an administrator's. If no polkit agent is running, pkexec may ask in the terminal instead, or fail, and then campermit suggests `sudo`.

The dialog only works for the installed `/usr/bin/campermit`. A copy anywhere else, such as one in a virtual environment or from pipx, tells you to use `sudo` instead, because letting root run a file you can edit would not be safe.

### Changing the defaults

The package installs three polkit actions, `org.campermit.disable`, `org.campermit.enable` and `org.campermit.forget`, and all of them ask for a password. To change that, add a rules file. To let `disable` run without a password when you are at the machine, create `/etc/polkit-1/rules.d/50-campermit.rules`:

```js
polkit.addRule(function(action, subject) {
    if (action.id == "org.campermit.disable" && subject.local && subject.active) {
        return polkit.Result.YES;
    }
});
```

polkit picks the file up on its own. Use `org.campermit.enable` or `org.campermit.forget` instead to do the same for those commands. Delete the file to go back to asking.

## Keeping a camera off

`disable` lasts until the next reboot. To keep a camera off, add `--persist`:

```
$ campermit disable 3-6 --persist
Disabled 3-6:1.0  HP Wide Vision HD Camera
3-6:1.0 will stay disabled after a reboot or replug
```

campermit saves the camera in `/etc/campermit/disabled`, one line per camera. A line holds the camera's ID, its USB ID and the USB controller it is on:

```
3-6:1.0 0408:5482 0000:00:14.0
```

A udev rule runs `campermit restore ID` each time a camera appears, at boot or when you plug it in. `restore` turns the camera off again if it matches a saved line, and does nothing otherwise. You don't need to run it yourself. The camera is on briefly at boot, until its driver attaches and the rule runs.

Turning a camera on, with `enable` or `toggle`, takes it off the saved list, so it stays on. To keep it off again, use `disable --persist`. `disable --all --persist` saves every camera that `list` shows, except any that another driver holds.

### How a camera is recognized

A saved line matches a camera when the controller, the port and the USB ID all agree. The first number in an ID like `3-6:1.0` is a bus number, and campermit ignores it, because the kernel can number buses differently from one boot to the next. In practice:

- The same camera in the same port is turned off again.
- The same camera in another port is left on. Run `disable --persist` for it again, and `forget` the old line.
- A different camera model in the saved port is left on too.
- Two cameras of the same model that swap ports can't be told apart.

Moving a camera to another port, or putting a different camera in its port, has not been tried with real hardware. The tests cover it against a fake `/sys`.

### Seeing and changing what is saved

`list` marks the cameras that are kept off, and shows any saved camera that is not connected:

```
$ campermit list
ID       NAME                      USB ID     STATE                NODES
3-6:1.0  HP Wide Vision HD Camera  0408:5482  disabled (kept off)

Saved to stay off, but no connected camera matches:
  2-6:1.0 1234:abcd 0000:00:0d.0
To forget one, run: campermit forget 2-6:1.0
```

- `enable ID` turns on a connected camera and takes it off the saved list.
- `forget ID` is for a saved camera that is not connected, for example one you moved to another port or no longer own. It asks for a password like the other commands. For a connected camera it tells you to use `enable`.

The saved file is plain text, but use `enable` and `forget` instead of editing it.

## Troubleshooting

**`No USB cameras found.`** Your camera may not be a USB camera. Many newer laptops have a built-in MIPI camera, which campermit can't see. When it finds other video devices, `list` mentions them.

**`this needs root. The password prompt only works for the installed /usr/bin/campermit`.** You are running a copy that is not the installed one, such as one in a virtual environment. Run it with `sudo`, and give the full path if `sudo` can't find it.

**`pkexec was not found`.** polkit is not installed. Install it, or use `sudo`.

**Password prompts stopped working for about ten minutes.** A wrong password or a dismissed dialog counts as a failed login. On systems that use `pam_faillock`, as Arch does, a few of those in a row lock password prompts for about ten minutes, `sudo` included. That is true of every password dialog on the system, not only this one.

**`the uvcvideo driver is not loaded`.** Load it with `sudo modprobe uvcvideo`. It is usually missing because it was unloaded or blacklisted.

**A camera I plugged back in turns itself off.** It is on the saved list, and `campermit list` shows it as `disabled (kept off)`. Run `campermit enable ID` to stop that.

**`list` shows `enabled (should be off)`.** The camera is saved, but it is still on. The udev rule is probably missing, because only the Arch package installs it for you, as `/usr/lib/udev/rules.d/99-campermit.rules`. `campermit disable ID` turns the camera off now.

**`list` says `Saved to stay off, but no connected camera matches`.** The saved camera is unplugged, in another port, or a different model. Plug it back in, or run `campermit forget ID` to drop the saved line.

## Limits

- Only the camera's video is turned off. If the camera has a microphone, that is a
  separate part of the USB device, and campermit does not touch it.
- It stops ordinary programs from using the camera. Anything running as root can
  turn the camera back on, so it is no protection against malware that already
  has root.
- USB cameras only. Many newer laptops have a built-in camera that is not USB
  (MIPI). campermit can't see or control those. When it finds no USB camera but
  other video devices exist, `list` says so.
- A camera that another driver already holds is left alone and reported.
- It has only been tested on one laptop with one camera: an HP Wide Vision HD
  Camera on kernel 7.3, CachyOS. [docs/hardware-notes.md](docs/hardware-notes.md)
  lists what has been checked.

## Why not unload or blacklist the driver?

`sudo modprobe -r uvcvideo` also turns cameras off, but it affects every UVC
camera at once, capture cards included, and it usually refuses while a program is
using one. Blacklisting `uvcvideo` is all-or-nothing as well, and only takes
effect at the next boot. campermit turns off just the camera you name, works while
a program is using it, and turns it back on without loading or unloading
anything. If your laptop has a single camera you never use, blacklisting is
simpler and may be all you need.

## Uninstalling

Uninstalling campermit does not change any camera. To get one back right away,
run `campermit enable --all` before removing it, or reboot. If campermit is
already gone, this does the same by hand (use your camera's ID):

```
echo '3-6:1.0' | sudo tee /sys/bus/usb/drivers/uvcvideo/bind
```

On Arch, remove it with `sudo pacman -R campermit`. If you installed it by hand, remove the rule and the install:

```
sudo rm /etc/udev/rules.d/99-campermit.rules /usr/local/bin/campermit
sudo rm -r /opt/campermit
sudo udevadm control --reload
```

The saved list in `/etc/campermit/disabled` is not part of the package, so it stays. If you install campermit again later, the cameras still on it are turned off again. Delete the `/etc/campermit` folder if you don't want that.

## For scripts

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
      "nodes": ["/dev/video0", "/dev/video1"],
      "kept_off": false
    }
  ]
}
```

`state` is `enabled`, `disabled`, or `other` (bound to a different driver, named in
`driver`). `kept_off` is `true` when the camera is on the saved list. New fields
may be added. `schema_version` changes only if a field is renamed or removed.

Exit codes: `0` when the camera ended up as asked, `1` when something failed,
`2` for a usage mistake. `126` means the password dialog was dismissed, and `127`
means polkit couldn't ask at all.

## Development

```
python3 -m venv .venv
.venv/bin/pip install -e . --group dev
.venv/bin/pytest
.venv/bin/ruff check
.venv/bin/ruff format --check
```

`--group` needs pip 25.1 or newer.

The tests run against a fake `/sys` tree, so they need no camera and no root.

## License

MIT. See [LICENSE](LICENSE).