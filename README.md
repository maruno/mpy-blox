# Mpy-BLOX
MicroPython building blox for ESP32-based devices.
This framework is a hobby project intended to make my life easier when working
on IoT MicroPython projects with the ESP32 microcontroller, mostly for home automation.

The framework can be used in two ways:
* Library only: Use the library or parts of it with your own `main.py`.
* App managed: The Mpy-BLOX framework provides it's own `main.py` and starts an asyncio loop.
User entrypoint will be expected in module `user_main` as `async def user_main()`.

*This project should not be considered production quality. Use at your own risk.*

## Configuration
There's 2 config locations, the main config is loaded from `settings.json`.
There is also a secured configuration that should be provisioned once.
This, for now, can only be done using an auto-deleted `provision.json`.
The secured configuration is stored insude of ESP32-NVS, *weakly* encrypted with the *device ID*.

In the examples a sample `settings.json` and `provision.json` is provided.

## MQTT OTA update channel
The framework can update it's MicroPython-based code over MQTT, listening for an update list over a channel topic.
When instructed, or automatically, it is then able to subscribe to receive the update files over the MQTT connection.
The updates over this update channel are much faster than over the USB-serial connection.

Two types of updates are supported:
* `wheel`: Micropython wheel packages, most likely the library package of this framework. :)
* `src`: Various source files, indicated by a path. Use this to update user_main or settings remotely.

In the examples a sample of the JSON payload on the update channel is provided in `update-channel.json`.
The framework expects this in topic `mpypi/channels/{update.channel}` where `update.channel` is sourced from settings.

The update files themselves need to be send as binaries to `mypypi/packages/{pkg_id}` where `pkg_id` is one of:
* `pkg_sha256` for type `wheel`.
* `path` for type `src`.

## Makefile instructions
The Makefile provides a simple interface to install and provision a device with the Mpy-BLOX framework.

### Requirements
The buildsystem uses the default MicroPython tool *mpremote* to communicate with your board.

* This project assumes micropython **v1.22** source level and **mpy6** bytecode version!
* Currently library 'zlib' is required to be installed or available as a frozen module.
* When using **WSL2 on Windows**: the win32 version of *mpremote* is required, because of 
missing direct serial communication on WSL2. There may be limitations but seems to work well through /mnt.
* Micropython CLI-utilities, including *mpremote* and *mpy-cross*.

### Device selection
The Make variable `DEVICE` allows you to set the device to connect to, otherwise the first device found is used.
Be sure to set `DEVICE` when having multiple (serial) devices connected, e.g.: `make DEVICE=COM4 repl`.

### Install lib/app framework
* deploy-lib: Installs the mpy_blox library to /lib to use Mpy-BLOX as as library-only framework.
* deploy-app: Installs main.py, settings file and provisioning for the full Mpy-BLOX managed app framework.

### Remove lib framework
* unprovision: Clears secure config part.
* purge-lib: Removes all /lib libraries.

### Misc
* repl: Open a REPL
* mounted-repl: Open a REPL with the current directory mounted as a remote filesystem.
