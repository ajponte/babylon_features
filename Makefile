# ==============================================================================
# babylon_features Makefile
#
# Centralized automation harness for quality gates, testing, linting,
# documentation auditing, and packaging.
# ==============================================================================

SHELL := /usr/bin/env bash

.PHONY: all help check-quality lint typecheck fmt test verify verify-docs verify-strict clean dist

all: verify ## Run complete verification gate (code, tests, docs, secrets)

verify: ## Run comprehensive verification gate (formatting, linting, typing, testing, docs audit, secret scan)
	@./scripts/verify.sh

verify-strict: ## Run complete verification gate in strict mode (fails if docs not synchronized with code changes)
	@./scripts/verify.sh --strict

verify-docs: ## Audit documentation, path privacy, and spec synchronization only
	@./scripts/verify.sh --docs-only

check-quality: lint typecheck ## Run linting and static type checking

fmt: ## Format codebase with black
	poetry run black features tests/datalake

lint: ## Run static analysis with pylint
	poetry run pylint features/datalake features/processor.py features/vectorstore $$(compgen -G 'features/tools/*.py' 2>/dev/null || true)

typecheck: ## Run static type checking with mypy
	poetry run mypy features/datalake $$(compgen -G 'features/tools/*.py' 2>/dev/null || true)

test: ## Run unit tests with pytest
	poetry run pytest tests/datalake/test_repository.py -v

test-all: ## Run full test suite across the repository
	poetry run pytest tests -v

dist: ## Build package distribution and zip module artifact
	tox -e dist

clean: ## Remove caches, build artifacts, and coverage files
	rm -rf .pytest_cache .mypy_cache .tox dist *.zip
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

help: ## Show available Makefile targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
