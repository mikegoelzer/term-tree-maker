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

.PHONY: test clean venv dev-venv publish-patch publish-minor publish-major release-latest install-dev install-min

venv: $(VENVDIR)/bin/python
$(VENVDIR)/bin/python:
	$(UV) venv --seed

dev-venv: venv
	$(UV) venv $(VENVDIR) --clear --seed --find-links $(LOCAL_CURVPYUTILS_PATH) --find-links $(LOCAL_CURVTOOLS_PATH)

install-dev: dev-venv
	$(UV) pip install --editable .[dev] --editable $(LOCAL_CURVPYUTILS_PATH) --editable $(LOCAL_CURVTOOLS_PATH) --find-links $(LOCAL_CURVPYUTILS_PATH) --find-links $(LOCAL_CURVTOOLS_PATH) || true; \
		echo "✓ Installed .[dev]...";
	$(UV) tool install --editable $(PKG_TERM_TREE_MAKER_PATH)[dev] --with-editable $(LOCAL_CURVPYUTILS_PATH) --with-editable $(LOCAL_CURVTOOLS_PATH) && \
		echo "✓ Installed $(PKG_TERM_TREE_MAKER)[dev]..."; 
	@# Edit shell's rc file to keep the PATH update persistent
	@$(UV) tool update-shell -q || true; \
		echo "✓ Updated shell to use the new $(notdir $(PKG_TERM_TREE_MAKER))[dev]...";
	@# $(UV) pip install --editable $(LOCAL_CURVPYUTILS_PATH) && \
	# 	echo "✓ Re-installed $(LOCAL_CURVPYUTILS_PATH)...";
	@# $(UV) pip install --editable $(LOCAL_CURVTOOLS_PATH) && \
	# 	echo "✓ Re-installed $(LOCAL_CURVTOOLS_PATH)...";
	@echo "⚠️ You need to run \`install.sh\` once (from a local GUI desktop session) to complete the installation"

# does installl-min + uv tool install's + create desktop_env_wrapper and profile
install: install-min
	@$(UV) tool install --editable $(PKG_TERM_TREE_MAKER)
	@echo "✓ All CLI tools (editable) available on PATH"
	@# Edit shell's rc file to keep the PATH update persistent
	@$(UV) tool update-shell -q || true
	@echo "⚠️ You need to run \`install.sh\` once (from a local GUI desktop session) to complete the installation"

# installs only the package (in editable mode)
install-min: venv
	@echo "🔄 Installing editable install of term-tree-maker..."
	@if $(UV) pip show -q $(PKG_TERM_TREE_MAKER) >/dev/null 2>&1; then \
		echo "✓ $(PKG_TERM_TREE_MAKER) already installed"; \
	else \
		$(UV) pip install -e $(PKG_TERM_TREE_MAKER_PATH); \
		echo "✓ Installed $(PKG_TERM_TREE_MAKER)..."; \
	fi;

test:
	uv run pytest

clean:
	@$(UV) tool uninstall $(PKG_TERM_TREE_MAKER) || true; \
		echo "✓ Uninstalled $(PKG_TERM_TREE_MAKER)...";
	@$(UV) pip uninstall $(PKG_TERM_TREE_MAKER)[dev] || true; \
		echo "✓ Uninstalled $(PKG_TERM_TREE_MAKER)[dev]...";
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
	uv run python $(BUMP_SCRIPT) patch --push
	$(MAKE) release-latest

publish-minor: test
	uv run python $(BUMP_SCRIPT) minor --push
	$(MAKE) release-latest

publish-major: test
	uv run python $(BUMP_SCRIPT) major --push
	$(MAKE) release-latest

release-latest:
	@version="$$(uv run python $(BUMP_SCRIPT) --show-latest)" ; \
	tag="$(TAG_PREFIX)$$version" ; \
	gh release create "$$tag" --title "term-tree-maker v$$version" --notes "Automated release $$tag"

