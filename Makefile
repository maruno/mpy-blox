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

.PHONY: version
dist-version:
	@echo "$(DIST_VERSION)"

.PHONY: clean
clean:
	@rm -rf dist

.PHONY: dist
dist: clean
	@poetry build
	@echo Building micropython optimized wheel
	@cd dist; wheel unpack $(WHEEL_VERSION)-py3-none-any.whl
	@echo "Byte-compiling for micropython"
	@cd dist/$(WHEEL_VERSION); for py_file in `find . -name "*.py"`; do mpy-cross $${py_file} && rm $${py_file}; done
	@cd dist/$(WHEEL_VERSION)/$(WHEEL_VERSION).dist-info; echo "c\nTag: mpy-bytecode-esp32\n.\nw\nq" | ed WHEEL > /dev/null
	@cd dist; wheel pack $(WHEEL_VERSION); rm $(WHEEL_VERSION)-py3-none-any.whl
	@cd dist; rm -r $(WHEEL_VERSION)
	@echo "Creating deployment hardlink"
	@cd dist; ln $(WHEEL_VERSION)-mpy-bytecode-esp32.whl mpy_blox-latest-mpy-bytecode-esp32.whl

.PHONY: deploy-lib
deploy-lib: dist
	@echo "Deploying $(DIST_VERSION) lib to device"
	@$(MPREMOTE_CMD) mount . run scripts/deploy_wheel.py

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
	@$(MPREMOTE_CMD) mount . repl
