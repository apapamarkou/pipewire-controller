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


## Installation Instructions

1. **Install dependencies:**

    - **Arch Linux, Manjaro, Garuda**
    ```bash
    sudo pacman -S python-pyqt5 pipewire
    ```

    - **RedHat, Fedora**
    ```bash
    sudo dnf install python3-qt5 pipewire
    ```

    - **OpenSUSE**
    ```bash
    sudo zypper install python3-qt5 pipewire
    ```

    - **Solus**
    ```bash
    sudo eopkg install python3-qt5 pipewire
    ```

     - **Debian, Ubuntu, Mint**
    ```bash
    sudo apt-get install python3-pyqt5 pipewire
    ```

   - **Slackware**   
   You may need to compile PyQt5 and PipeWire from source or find packages suitable for Slackware.


2. **Download and set up the script:**

    ```bash
    mkdir -p ~/Applications
    git clone https://github.com/apapamarkou/pipewire_controller.git ~/Applications/pipewire_controller
    chmod +x ~/Applications/pipewire_controller/pipewire_controller.py
    ```


3. **Add to startup:**

    - **KDE Plasma:** Go to `System Settings` -> `Startup and Shutdown` -> `Autostart` -> `Add Login Script` and point to `~/Applications/pipewire_controller/pipewire_controller.py`.

    - **GNOME:** Open `Startup Applications`, click `Add`, and point to `~/Applications/pipewire_controller/pipewire_controller.py`.

    - **XFCE:** Go to `Session and Startup` -> `Application Autostart`, click `Add`, and enter the command `~/Applications/pipewire_controller/pipewire_controller.py`.

    - **i3/Sway:** Add the script to your `~/.config/i3/config` or `~/.config/sway/config` file using `exec --no-startup-id ~/Applications/pipewire_controller/pipewire_controller.py`.


## Running the Script

The script is designed to be run as a startup application. Once installed and configured to run at startup, it will provide a tray icon allowing you to adjust the samplerate and buffer size of PipeWire.

For any issues or contributions, please visit the [GitHub repository](https://github.com/yourusername/pipewire_controller).

## License

This script is licensed under the GNU License. See the [LICENSE](LICENSE) file for details.


