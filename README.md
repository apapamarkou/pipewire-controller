# PipeWire Controller

![Peek 2024-07-04 02-18](https://github.com/apapamarkou/pipewire_controller/assets/42995877/32536db2-a461-4078-896c-573e77dd7092)

A simple to install and use tray icon to control the samplerate and buffersize when using [PipeWire](https://pipewire.org/) audio server.

## Features

- Change the samplerate and buffer size of [PipeWire](https://pipewire.org/) from a system tray icon.
- Save and load settings automatically.
- Support for any Linux desktop environment or window manager with a system tray visible.

## Dependencies

To run this application, you need the following dependencies:

- Python 3
- PyQt5 or PyQt6 (use -qt6 flag)
- PipeWire utilities (`pw-metadata` command)
- Git
- Wget

## How do I install those "dependencies"?

### Examples

- **Arch Linux, Manjaro, Garuda**
```
sudo pacman -S --needed python-pyqt5 pipewire git wget
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

Note: replace `python3-qt5` with `python3-qt5` if you want to use Qt6

## How to Install/Update Pipewire Controller

Copy the following command, paste it in a terminal and hit [ENTER]. Thats it!
```
QT_PLATFORM=5 wget -qO- https://raw.githubusercontent.com/apapamarkou/pipewire-controller/main/src/pipewire-controller-git-install | bash
```

Note: replace `QT_PLATFORM=5` with `QT_PLATFORM=6` if you want to use Qt6

## How to Uninstall Pipewire Controller

Copy the following command, paste it in a terminal and hit [ENTER]. Thats it!
```
wget -qO- https://raw.githubusercontent.com/apapamarkou/pipewire-controller/main/src/pipewire-controller-git-uninstall | bash
```

## Acknowledgments

I would like to extend our heartfelt thanks to the following contributors:

- **@[ItzSelenux](https://github.com/ItzSelenux)**
- **@[Axel-Erfurt](https://github.com/Axel-Erfurt)**

Thank you for being a part of our project and helping make it better!

## License

This script is licensed under the GNU License. See the [LICENSE](LICENSE) file for details.


