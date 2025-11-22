SHELL := /bin/bash
BUMP_SCRIPT := scripts/bump_version.py
TAG_PREFIX := term-tree-maker-v

.PHONY: test clean publish-patch publish-minor publish-major release-latest

test:
	uv run pytest

clean:
	rm -rf build dist .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov

publish-patch: test
	uv run python $(BUMP_SCRIPT) patch --push
	$(MAKE) release-latest

publish-minor: test
	uv run python $(BUMP_SCRIPT) minor --push
	$(MAKE) release-latest

publish-major: test
	uv run python $(BUMP_SCRIPT) major --prompt-push
	$(MAKE) release-latest

release-latest:
	@version="$$(uv run python $(BUMP_SCRIPT) --show-latest)" ; \
	tag="$(TAG_PREFIX)$$version" ; \
	gh release create "$$tag" --title "term-tree-maker v$$version" --notes "Automated release $$tag"

