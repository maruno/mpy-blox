SPACE := $(eval) $(eval)
DIST_VERSION := $(subst $(SPACE),-,$(shell poetry version))

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
	@poetry build -f sdist
	@gzip -dc dist/$(DIST_VERSION).tar.gz | tar --delete $(DIST_VERSION)/PKG-INFO --delete $(DIST_VERSION)/pyproject.toml -o | gzip > dist/$(DIST_VERSION).upip.tgz

.PHONY: deploy-lib
deploy-lib: dist
	@echo "Deploying $(DIST_VERSION) lib to device"
	@$(MPREMOTE_CMD) cp dist/$(DIST_VERSION).upip.tgz :/deploy.tgz
	@$(MPREMOTE_CMD) run scripts/deploy.py
	@$(MPREMOTE_CMD) rm :/deploy.tgz

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
