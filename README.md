# Mpy-BLOX
MicroPython building blox for ESP32-based devices.
This framework is a hobby project intended to make my life easier when working
on IoT MicroPython projects with the ESP32 microcontroller, mostly for home automation.

The framework can be used in two ways:
* Library only: Use the library or parts of it with your own `main.py`
* App managed: The Mpy-BLOX framework provides it's own `main.py` and starts an asyncio loop.
User entrypoint will be expected in module `user_main` as `async def user_main()`

*This project should not be considered production quality. Use at your own risk.*

## Configuration
There's 2 config locations, the main config is loaded from `settings.json`.
There is also a secured configuration that should be provisioned once.
This, for now, can only be done using an auto-deleted `provision.json`.
The secured configuration is stored insude of ESP32-NVS, *weakly* encrypted with the *device ID*.

In the examples a sample `settings.json` and `provision.json` is provided.

## Makefile instructions
The Makefile provides a simple interface to install and provision a device with the Mpy-BLOX framework.

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
