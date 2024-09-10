# PipeWire Controller

![Peek 2024-07-04 02-18](https://github.com/apapamarkou/pipewire_controller/assets/42995877/32536db2-a461-4078-896c-573e77dd7092)

A simple to install and use tray icon to control the samplerate and buffersize when using PipeWire audio server.

## Features

- Change the samplerate and buffer size of PipeWire from a system tray icon.
- Save and load settings automatically.
- Support for any Linux desktop environment or window manager with a system tray visible.

## Dependencies

To run this application, you need the following dependencies:

- Python 3
- PyQt5
- PipeWire utilities (`pw-metadata` command)
- Git
- Wget

## How do I install those "dependencies"?

### Examples

**Arch Linux, Manjaro, Garuda**
```
sudo pacman -S python-pyqt5 pipewire git wget
```

- **RedHat, Fedora** 
```
sudo dnf install python3-qt5 pipewire git wget
```

- **OpenSUSE** 
```
sudo zypper install python3-qt5 pipewire git wget
```

- **Solus** 
```
sudo eopkg install python3-qt5 pipewire git wget
```

- **Debian, Ubuntu, Mint** 
```
sudo apt-get install python3-pyqt5 pipewire git wget
```

## How to Install Piewire Controller

Copy the following command, and paste it in a terminal and hit [ENTER]. Thats it!
```
wget -qO- https://raw.githubusercontent.com/apapamarkou/pipewire-controller/main/src/pipewire-controller-git-install | bash
```

## How to Uninstall Piewire Controller

Copy the following command, and paste it in a terminal and hit [ENTER]. Thats it!
```
wget -qO- https://raw.githubusercontent.com/apapamarkou/pipewire-controller/main/src/pipewire-controller-git-uninstall | bash
```

## License

This script is licensed under the GNU License. See the [LICENSE](LICENSE) file for details.


