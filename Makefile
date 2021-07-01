SPACE := $(eval) $(eval)
DIST_VERSION := $(subst $(SPACE),-,$(shell poetry version))

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

