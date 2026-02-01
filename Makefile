SPACE := $(eval) $(eval)
POETRY_VERSION = $(shell poetry version)
DIST_VERSION := $(subst $(SPACE),-,$(POETRY_VERSION))
WHEEL_VERSION := $(subst $(SPACE),-,$(subst -,_,$(POETRY_VERSION)))

IS_WSL2 := $(findstring WSL2,$(shell uname -r))
ifeq ($(IS_WSL2),WSL2)
$(warning WSL2 detected: Using Windows MPRemote)
MPREMOTE_CMD := mpremote.exe
else
MPREMOTE_CMD := mpremote
endif

ifdef DEVICE
MPREMOTE_CMD := $(MPREMOTE_CMD) connect $(DEVICE)
endif

ifndef UNIX_MARCH
UNIX_MARCH=x64
endif

# Platform-specific module exclusions
# - app.py: Full managed app run mode not available, limited UNIX version is
# - secure_nvs.py: ESP32-specific NVS storage
# - socket_uart.py: Hardware UART pin access
# - input/: Hardware input pin modules
# - serial/: Serial hardware communication
# - sensor/: Hardware sensor drivers
# - sound/: Sound/I2S hardware modules
# - mqtt/hass/*.py: HASS modules with direct hardware inputs
ESP32_ONLY_PATTERNS := \
  ./mpy_blox/app.py \
  ./mpy_blox/config/secure_nvs.py \
  ./mpy_blox/socket_uart.py \
  ./mpy_blox/input/\* \
  ./mpy_blox/serial/\* \
  ./mpy_blox/sensor/\* \
  ./mpy_blox/sound/\* \
  ./mpy_blox/mqtt/hass/on_off_toggle.py \
  ./mpy_blox/mqtt/hass/switch.py \
  ./mpy_blox/mqtt/hass/light.py

# - unix/: UNIX platform specific modules
UNIX_ONLY_PATTERNS := \
  ./mpy_blox/unix/\*

.PHONY: version
dist-version:
	@echo "$(DIST_VERSION)"

.PHONY: clean
clean:
	@rm -rf dist

.PHONY: dist-src
dist-src: clean
	@poetry build

.PHONY: list-exclusions
list-exclusions: dist-src
	@cd dist; wheel unpack $(WHEEL_VERSION)-py3-none-any.whl
	@echo "Files that will be excluded from UNIX build (ESP32-only):"
	@cd dist/$(WHEEL_VERSION); \
		for pattern in $(ESP32_ONLY_PATTERNS); do \
			find . -wholename "$$pattern" 2>/dev/null; \
		done | sort -u || echo "  (none)"
	@echo ""
	@echo "Files that will be excluded from ESP32 build (UNIX-only):"
	@cd dist/$(WHEEL_VERSION); \
		for pattern in $(UNIX_ONLY_PATTERNS); do \
			find . -wholename "$$pattern" 2>/dev/null; \
		done | sort -u || echo "  (none)"
	@cd dist; rm -r $(WHEEL_VERSION)

.PHONY: dist-esp32
dist-esp32: dist-src
	@echo Building micropython optimized wheel for ESP32
	@cd dist; wheel unpack $(WHEEL_VERSION)-py3-none-any.whl
	@echo "Byte-compiling for micropython (ESP32)"
	@cd dist/$(WHEEL_VERSION); for py_file in `find . -name "*.py"`; do mpy-cross -march=xtensawin $${py_file} && rm $${py_file}; done
	@cd dist/$(WHEEL_VERSION)/$(WHEEL_VERSION).dist-info; echo "c\nTag: mpy6-bytecode-esp32\n.\nw\nq" | ed WHEEL > /dev/null
	@cd dist; wheel pack $(WHEEL_VERSION); rm $(WHEEL_VERSION)-py3-none-any.whl
	@cd dist; rm -r $(WHEEL_VERSION)
	@echo "Creating deployment hardlink (ESP32)"
	@cd dist; ln $(WHEEL_VERSION)-mpy6-bytecode-esp32.whl mpy_blox-latest-mpy6-bytecode-esp32.whl

.PHONY: dist-unix
dist-unix: dist-src
	@echo Building micropython optimized wheel or UNIX
	@cd dist; wheel unpack $(WHEEL_VERSION)-py3-none-any.whl
	@echo "Removing ESP32-specific modules"
	@cd dist/$(WHEEL_VERSION); \
		for pattern in $(ESP32_ONLY_PATTERNS); do \
			find . -wholename "$$pattern" -delete 2>/dev/null; \
		done
	@echo "Byte-compiling for micropython (platform-independant/UNIX)"
	@cd dist/$(WHEEL_VERSION); for py_file in `find . -name "*.py"`; do mpy-cross -march=$(UNIX_MARCH) $${py_file} && rm $${py_file}; done
	@cd dist/$(WHEEL_VERSION)/$(WHEEL_VERSION).dist-info; echo "c\nTag: mpy6-bytecode-unix_$(UNIX_MARCH)\n.\nw\nq" | ed WHEEL > /dev/null
	@cd dist; wheel pack $(WHEEL_VERSION); rm $(WHEEL_VERSION)-py3-none-any.whl
	@cd dist; rm -r $(WHEEL_VERSION)
	@echo "Creating deployment hardlink (UNIX)"
	@cd dist; ln $(WHEEL_VERSION)-mpy6-bytecode-unix_$(UNIX_MARCH).whl mpy_blox-latest-mpy6-bytecode-unix_$(UNIX_MARCH).whl

.PHONY: dist
dist: dist-esp32

.PHONY: deploy-lib
deploy-lib: dist
	@echo "Deploying $(DIST_VERSION) lib to device"
	-@$(MPREMOTE_CMD) mkdir /dist
	@$(MPREMOTE_CMD) cp dist/mpy_blox-latest-mpy6-bytecode-esp32.whl :/dist/mpy_blox-latest-mpy6-bytecode-esp32.whl
	@$(MPREMOTE_CMD) mount . run scripts/mount_enforcer.py run scripts/deploy_wheel.py
	@echo "Deployment succeeded, resetting device"
	@$(MPREMOTE_CMD) reset

.PHONY: purge-lib
purge-lib:
	@echo "Purging device of all libraries"
	@$(MPREMOTE_CMD) run scripts/purge.py

.PHONY: provision
provision:
	@[ -f provision.json ] && $(MPREMOTE_CMD) cp provision.json :/provision.json

.PHONY: unprovision
unprovision:
	@echo "Clearing provisioning config from device"
	@$(MPREMOTE_CMD) run scripts/unprovision.py

.PHONY: deploy-app
deploy-app: provision
	@echo "Deploying $(DIST_VERSION) app to device"
	@$(MPREMOTE_CMD) cp settings.json :/settings.json
	@$(MPREMOTE_CMD) cp main.py :/main.py

.PHONY: deploy-user
deploy-user:
	@echo "Deploying $(DIST_VERSION) user_main to device"
	@$(MPREMOTE_CMD) cp user_main.py :/user_main.py

.PHONY: purge-app
purge-app:
	@echo "Purging device of main app!"
	@$(MPREMOTE_CMD) rm :/settings.json
	@$(MPREMOTE_CMD) rm :/main.py

.PHONY: repl
repl:
	@$(MPREMOTE_CMD) repl

.PHONY: mounted-repl
mounted-repl:
	@$(MPREMOTE_CMD) mount . run scripts/mount_enforcer.py repl
