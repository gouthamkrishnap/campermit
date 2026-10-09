# CamPermit

A Linux CLI utility for controlling camera availability at the device and driver level.

CamPermit discovers supported USB Video Class (UVC) cameras and lets you inspect, enable, disable, or toggle their availability through Linux sysfs.

## Features

- Discover and list supported cameras.
- Inspect camera status and device information.
- Enable, disable, or toggle an individual camera.
- Enable or disable all discovered cameras.
- Produce machine-readable JSON output.
- Verify state changes and report operation errors.
- Coordinate operations using a lock.

## Requirements

- Linux
- Python 3.11 or later
- A supported USB Video Class (UVC) camera
- Appropriate permissions to perform camera-control operations

## Installation

The recommended way to install CamPermit as a command-line application is with [pipx](https://pipx.pypa.io/stable/installation/). It installs CamPermit in an isolated Python environment and avoids modifying the system Python installation.

### 1. Install pipx

On Arch Linux:

```bash
sudo pacman -S python-pipx
```

For other Linux distributions, follow the [pipx installation instructions](https://pipx.pypa.io/stable/installation/).

### 2. Install CamPermit

Clone the repository and install the project:

```bash
git clone https://github.com/gouthamkrishnap/campermit.git
cd campermit
pipx install .
```

Verify the installation:

```bash
campermit --version
campermit --help
```

If the `campermit` command is not found, run:

```bash
pipx ensurepath
```

Then open a new terminal so the updated `PATH` takes effect.

## Usage

### List cameras

```bash
campermit list
campermit list --json
```

### Check camera status

```bash
campermit status 1
campermit status 3-6
campermit status 0408:5482
```

A selector can be a camera ID, USB bus path, or vendor ID and product ID (`VID:PID`).

### View camera information

```bash
campermit info 1
campermit info --all
campermit info --all --json
```

### Enable a camera

```bash
campermit enable 1
campermit enable 3-6
campermit enable 0408:5482
```

### Disable a camera

```bash
campermit disable 1
campermit disable 3-6
campermit disable 0408:5482
```

### Toggle a camera

```bash
campermit toggle 1
```

### Enable or disable all cameras

```bash
campermit enable --all
campermit disable --all
```

Use `--json` with supported commands when you need machine-readable output.

For the complete list of options, run:

```bash
campermit --help
campermit COMMAND --help
```

Replace `COMMAND` with a subcommand such as `enable`, `disable`, or `info`.

## Permissions

Camera-control operations write to Linux sysfs interfaces and may require elevated privileges. Use the permissions appropriate for your system.

If your account lacks the required permissions, you may need to run the command with `sudo`, depending on your system configuration:

```bash
sudo campermit disable 1
sudo campermit enable 1
```

## Limitations

- The initial release targets supported USB Video Class (UVC) cameras on Linux.
- Disabling a camera at the driver-interface level is different from physically disconnecting it.
- USB resets, device re-enumeration, or suspend/resume may change the camera's state. Persistence across these events is not guaranteed.
- Desktop-environment integrations and automatic persistence are outside the scope of this initial CLI release.

## Development

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the package in editable mode and install the test dependency:

```bash
python -m pip install -e .
python -m pip install pytest
```

Run the test suite:

```bash
pytest -q
```

## License

CamPermit is distributed under the MIT License. See the [LICENSE](LICENSE) file for details.