SHELL := /bin/bash
BUMP_SCRIPT := scripts/bump_version.py
TAG_PREFIX := term-tree-maker-v
VENVDIR := .venv
UV := uv
PKG_TERM_TREE_MAKER_PATH := $(shell realpath .)
PKG_TERM_TREE_MAKER := term-tree-maker
DEFAULT_OUTPUT_DIR := output

LOCAL_CURVPYUTILS_PATH := ../../../curv-python/packages/curvpyutils
LOCAL_CURVTOOLS_PATH := ../../../curv-python/packages/curvtools

.PHONY: test clean venv upgrade-venv-for-dev publish-patch publish-minor publish-major release-latest install-dev install-min install-tools-dev

venv: $(VENVDIR)/bin/python
$(VENVDIR)/bin/python:
	$(UV) venv --seed $(VENVDIR)
	$(UV) sync --extra dev

upgrade-venv-for-dev: venv
	$(UV) pip install -e $(LOCAL_CURVPYUTILS_PATH) -e $(LOCAL_CURVTOOLS_PATH)

install-tools-dev:
	$(UV) tool install --editable $(PKG_TERM_TREE_MAKER_PATH)[dev] --with-editable $(LOCAL_CURVPYUTILS_PATH) --with-editable $(LOCAL_CURVTOOLS_PATH) && \
		echo "✓ Installed $(PKG_TERM_TREE_MAKER)[dev] as tool..." \
		|| echo "✗ Failed to install $(PKG_TERM_TREE_MAKER)[dev]..."
	@# Edit shell's rc file to keep the PATH update persistent
	@$(UV) tool update-shell -q && \
		echo "✓ Updated shell to use the new $(notdir $(PKG_TERM_TREE_MAKER))[dev]..." \
		|| echo "✗ Failed to update shell..."
	@echo "⚠️ You need to run \`install.sh\` once (from a local GUI desktop session) to complete the installation"

# alias for install-min
install: install-min

install-dev: install-min upgrade-venv-for-dev install-tools-dev
	@echo "✓ term-tree-maker, global CLI tools + local curvpyutils/curvtools installed in $(VENVDIR)"

# installs only the package (in editable mode)
install-min: venv
	@echo "🔄 Installing editable install of term-tree-maker..."
	@if $(UV) pip show -q $(PKG_TERM_TREE_MAKER) >/dev/null 2>&1; then \
		echo "✓ $(PKG_TERM_TREE_MAKER) already installed"; \
	else \
		$(UV) pip install -e $(PKG_TERM_TREE_MAKER_PATH); \
		echo "✓ Installed $(PKG_TERM_TREE_MAKER)..."; \
	fi;

test: upgrade-venv-for-dev
	$(UV) run pytest

clean:
	@$(UV) tool uninstall $(PKG_TERM_TREE_MAKER) || true; \
		echo "✓ Uninstalled $(PKG_TERM_TREE_MAKER)...";
	@rm -rf build dist .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.log" -exec rm -f {} + 2>/dev/null || true
	@find /tmp -type f -name "tree-*" -exec rm -f {} + 2>/dev/null || true
	@find "$(DEFAULT_OUTPUT_DIR)" -type f -name "*.png" -exec rm -f {} + 2>/dev/null || true
	@rmdir "$(DEFAULT_OUTPUT_DIR)" 2>/dev/null || true \
		echo "✓ Removed $(DEFAULT_OUTPUT_DIR)...";
	@[ -d "$(VENVDIR)" ] && { \
		$(RM) -rf $(VENVDIR) ; \
		echo "✓ Removed $(VENVDIR)"; \
	} || { \
		echo "✓ Skipping venv cleanup since $(VENVDIR) does not exist"; \
	}

publish-patch: test
	$(UV) run python $(BUMP_SCRIPT) patch --push
	$(MAKE) release-latest

publish-minor: test
	$(UV) run python $(BUMP_SCRIPT) minor --push
	$(MAKE) release-latest

publish-major: test
	$(UV) run python $(BUMP_SCRIPT) major --push
	$(MAKE) release-latest

release-latest:
	@version="$$($(UV) run python $(BUMP_SCRIPT) --show-latest)" ; \
	tag="$(TAG_PREFIX)$$version" ; \
	gh release create "$$tag" --title "term-tree-maker-v$$version" --notes "Automated release $$tag"

