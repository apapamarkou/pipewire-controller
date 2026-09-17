# Arch Setup guide

## Pipewire Patch Bay
```sh
sudo pacman -S --needed --noconfirm qpwgraph
```

## Pipewire Easy Effects
```sh
sudo pacman -S --needed --noconfirm easyeffects
```

## Pipewire Setup
In Arch pipewire is set. If not see [Arch wikki](https://wiki.archlinux.org/title/Main_page).

# Debian 13 

## Pipewire Setup
```sh
sudo apt install -y pipewire-jack pipewire-audio-client-libraries libspa-0.2-jack
systemctl --user --now enable wireplumber.service
sudo mkdir -p /etc/pipewire/media-session.d
sudo touch /etc/pipewire/media-session.d/with-jack
sudo cp /usr/share/doc/pipewire/examples/ld.so.conf.d/pipewire-jack-*.conf /etc/ld.so.conf.d/
sudo ldconfig
```

## Pipewire Patch Bay
```sh
sudo apt install -y qpwgraph
```

## Pipewire Easy Effects
```sh
sudo apt install -y easyeffects
```

# Fedora 44

## Pipewire Setup
In Fedora 44 pipewire is set


## Pipewire Patch Bay
```sh
sudo dnf install -y qpwgraph
```

## Pipewire Easy Effects
```sh
sudo dnf install -y easyeffects
```

# Ubuntu 26.04

## Pipewire Setup

```sh
sudo apt install -y pipewire-jack pipewire-audio-client-libraries libspa-0.2-jack
systemctl --user --now enable wireplumber.service
sudo mkdir -p /etc/pipewire/media-session.d
sudo touch /etc/pipewire/media-session.d/with-jack
sudo cp /usr/share/doc/pipewire/examples/ld.so.conf.d/pipewire-jack-*.conf /etc/ld.so.conf.d/
sudo ldconfig
```
## Pipewire Patch Bay
```sh
sudo apt install -y qpwgraph
```

## Pipewire Easy Effects
```sh
sudo apt install -y easyeffects
```