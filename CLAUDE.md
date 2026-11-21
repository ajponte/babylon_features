# CLAUDE.md for babylon_features

This quick-reference guide provides essential commands, architecture links, and development workflows for `babylon_features`.

---

## Documentation & Architecture References

- **[Subsystem Agent Guidelines](AGENTS.md)**: Primary persona, architecture overview, clean coding patterns, and Babylon 2.0 governance.
- **[Master Architecture Catalog](docs/specs/README.md)**: Architectural catalog, system sequence diagram, and cross-cutting invariants.
- **[Datalake Storage & Repository Spec](docs/specs/datalake-storage-repository.md)**: `TransactionDto`, `_apply_limit` query limits, and `BaseRepository` contracts.
- **[Vectorization & Processing Pipeline Spec](docs/specs/vectorization-processing-pipeline.md)**: `CollectionProcessor` lifecycle, chunking invariants, `VectorStore` port, and CLI specification.
- **[Agent Persona (Software Engineer)](docs/Agent.md)**: Prompt and expectations for feature pipeline engineering.
- **[Agent Persona (DevOps)](docs/Agent-Devops.md)**: CI/CD workflows, packaging, and artifact publishing.

---

## Commands Cheat Sheet

### Environment Setup
- **Install dependencies**: `poetry install`
- **Activate poetry shell**: `poetry shell`

### Testing & Quality Gates
- **Run all unit tests**: `poetry run pytest tests`
- **Run single test module**: `poetry run pytest tests/datalake/test_repository.py`
- **Run single test case**: `poetry run pytest tests/datalake/test_repository.py -k test_get_by_id_success`
- **Format code (in-place)**: `poetry run black features tests`
- **Check formatting (dry-run)**: `poetry run black features tests --check --diff`
- **Lint code**: `poetry run pylint --rc-file=.pylintrc features/`
- **Type check**: `poetry run mypy features`

### Tox Automation
- **Run full test suite across environments**: `tox`
- **Run unit tests only**: `tox -e pytest`
- **Run linter only**: `tox -e lint`
- **Verify formatting only**: `tox -e format`
- **Run typecheck only**: `tox -e typecheck`
- **Build wheel & zip artifact**: `tox -e dist`

### Vectorization & Pipeline Execution
- **Run manual vectorization (dry-run)**: `poetry run vectorize --dry-run`
- **Run manual vectorization (mutating)**: `poetry run vectorize`
- **Vectorize specific collection**: `poetry run vectorize --collection transactions_chase --limit 100`
- **Vectorize with explicit vector DB**: `poetry run vectorize --vector-db qdrant`
- **Run pipeline workflow**: `poetry run run-pipeline`
- **Run background daemon**: `poetry run python daemon.py`
- **Visualize embeddings scatterplot**: `poetry run python visualize.py`

### Packaging & Release
- **Build Python wheel & sdist**: `poetry build`
- **Generate ZIP distribution artifact**: `tox -e dist` (creates `babylon-features.zip`)
- **Upload artifact to GitHub Release**:
  ```bash
  python artifact_upload.py --repo <owner>/<repo> --tag <tag>
  ```

---

## Continuous Integration (CI/CD)

The GitHub Actions workflows (`.github/workflows/`) enforce quality checks on every push and pull request to `main`:
- **lint**: `pylint --rc-file=.pylintrc features/`
- **format**: `black features --check --diff`
- **typecheck**: `mypy features`
- **test**: `pytest tests`

---

## Security & PII Rules

1. **Zero Real PII**: Never commit or log real financial transaction records, account numbers, or balances.
2. **Log Safety**: Keep logs generic and aggregate (`chunks_emitted`, `batch_number`, elapsed time).
3. **Synthetic Test Data**: Always use `new_valid_dto` domain builders or synthetic fixtures in tests.
4. **Secrets Management**: Dynamic credentials must be loaded via OpenBao (`features/config/hashicorp.py`) or local environment variables (`.env`). Never hardcode secrets.

---

## Git & Pull Request Governance

> [!IMPORTANT]
> **STRICT PULL REQUEST MERGE RESTRICTION**:
> Agents must **NEVER** merge pull requests (`gh pr merge`, GitHub API calls, or direct merges into `main`) without explicit user permission.
> Open the PR, verify CI checks pass, provide the PR URL and verification notes, and await user direction.
