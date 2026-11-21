# AGENTS.md for babylon_features

This guide defines operational principles, architecture, coding patterns, and governance standards for AI agents working within the `babylon_features` repository.

---

## Role & Persona

You are an expert Python AI/ML Engineer specializing in Python 3.13, MongoDB, LangChain, ChromaDB, Qdrant, and Retrieval-Augmented Generation (RAG) feature pipelines within the Babylon 2.0 financial intelligence platform.

You design maintainable, modular, and fault-tolerant data pipelines that extract financial transaction entities, construct semantic documents, split text into embeddings-ready chunks, and synchronize vectors across storage engines.

---

## Architecture Overview

`babylon_features` bridges raw bank and brokerage statement ingestion in the MongoDB datalake with downstream semantic retrieval and LLM agents. The subsystem is structured into four primary layers:

### 1. Datalake Persistence Layer (`features/datalake/`)
- **`TransactionDto`**: Canonical domain transfer object representing financial transactions (`id`, `amount`, `posting_date`, `description`, `details`, `transaction_type`, `check_num`).
- **Query Limit Guarding (`_apply_limit`)**: Strictly validates limit parameters on repository queries; rejects boolean values and non-integers with `TypeError`, and non-positive numbers with `ValueError`.
- **Repository Seams (`BaseRepository`, `TransactionRepository`)**: Encapsulate MongoDB and BSON driver-level exceptions (e.g., `InvalidId` returns `None` rather than raising driver exceptions). Delegates document mapping to `TransactionMapper`.
- **Connection & Session Management (`MongoClientFactory`, `UnitOfWork`)**: Resilient MongoDB client connection pooling and context-managed session/transaction handling.
- **Read-Only Invariant**: The datalake repository layer operates strictly read-only against transaction collections.

### 2. Processing & Vectorization (`features/processor.py`, `features/vectorstore/`, `features/rag/`)
- **`CollectionProcessor`**: Orchestrates batch collection extraction, increments batch counters, and coordinates document chunking and vector storage.
- **Fault-Tolerant Batch Isolation**: Document construction and chunking failures on individual transactions are logged and isolated; single-document exceptions never abort batch processing.
- **Chunking Strategy (`RecursiveCharacterTextSplitter`)**: Semantic chunking adhering strictly to standard boundaries: `chunk_size = 1000`, `chunk_overlap = 100`, and `add_start_index = True`.
- **Multi-Backend Vector Store (`VectorStore` ABC)**: Abstract port providing similarity search, bulk insertion, and collection querying with pluggable backends managed by `vector_store_factory`:
  - `ChromaVectorStore`: Embedded SQLite/DuckDB on-disk storage (`CHROMA_SQLITE_DIR`, `EMBEDDINGS_COLLECTION_CHROMA`).
  - `QdrantVectorStore`: Remote network service via REST/gRPC (`QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_COLLECTION`).

### 3. CLI Tooling & Entrypoints (`features/tools/`, `daemon.py`)
- **On-Demand Manual Vectorization (`poetry run vectorize`)**: Ad-hoc CLI (`python -m features.tools.run`) supporting collection filtering (`--collection`), record limits (`--limit`), vector backend selection (`--vector-db`), dry-run validation (`--dry-run`), and structured execution summary telemetry.
- **Pipeline Execution (`poetry run run-pipeline`)**: Automated end-to-end dataset generation and vectorization workflow.
- **Continuous Synchronization Daemon (`daemon.py`)**: Background daemon polling the datalake at configured intervals and updating vector indexes.

### 4. Configuration & Secrets (`features/config/`)
- **OpenBao Secrets Manager (`BaoSecretsManager`, `hashicorp.py`)**: Dynamic retrieval of datalake credentials (`MONGO_DB_HOST`, `MONGO_DB_PORT`, `MONGO_DB_USER`, `MONGO_DB_PASSWORD`) from HashiCorp Vault / OpenBao.
- **Declarative Loaders (`configuration_loaders.py`, `config.py`)**: Structured `required`, `required_secret`, and `optional` environment variable parsing with validation and type conversion.

---

## Canonical Architectural Specifications

Agents must adhere to the canonical technical specifications in `docs/specs/` before making architectural or behavioral changes:

- **[Master Architecture Catalog](docs/specs/README.md)**: Catalog index, end-to-end data flow, cross-cutting invariants, and repository directory structure.
- **[Datalake Storage & Repository Specification](docs/specs/datalake-storage-repository.md)**: `TransactionDto` contract, `_apply_limit` type guarding, `BaseRepository` query seams, driver exception encapsulation, and null-safe iterators.
- **[Vectorization & Processing Pipeline Specification](docs/specs/vectorization-processing-pipeline.md)**: `CollectionProcessor` batch lifecycle, fault-tolerant batch isolation, `VectorStore` port contracts, CLI flags, and summary reporting.
- **[Verification Harness & Quality Gates Specification](docs/specs/verification-and-quality.md)**: 6-gate verification pipeline (`make verify`), linting standards (pylint 10.00/10), testing rigor, and documentation audit rules.

---

## Automated Verification Harness & Makefile

This repository includes a centralized `Makefile` and verification script (`scripts/verify.sh`) matching the quality gates in `babylon_data_loader`:

```bash
# Run all 6 verification gates (formatting, linting, typing, tests, doc audit, secret scan)
make verify
# or
./scripts/verify.sh

# Run strict verification (fails if code changed without documentation updates)
make verify-strict

# Audit documentation, path privacy, and spec synchronization only
make verify-docs
```

### Makefile Target Reference
- `make verify`: Executes all 6 quality gates sequentially.
- `make check-quality`: Runs `pylint` and `mypy` static type checking.
- `make test`: Runs unit tests (`poetry run pytest tests/datalake/test_repository.py -v`).
- `make test-all`: Runs the entire pytest suite across the repository.
- `make fmt`: Auto-formats code with `black`.
- `make verify-docs`: Audits path privacy, relative link integrity, and documentation currency.
- `make clean`: Removes caches, coverage artifacts, and `.tox` directories.

---

## Development & Quality Commands

This project uses **Poetry** for dependency management and **Tox** for multi-environment test automation.

### Poetry Development Workflow
- **Install Dependencies**: `poetry install`
- **Run Pytest Suite**: `poetry run pytest tests`
- **Format Code**: `poetry run black features tests`
- **Check Formatting**: `poetry run black features tests --check --diff`
- **Run Linter**: `poetry run pylint --rc-file=.pylintrc features/`
- **Run Type Checker**: `poetry run mypy features`
- **Vectorize CLI**: `poetry run vectorize --dry-run` or `python -m features.tools.run --dry-run`
- **Run Pipeline**: `poetry run run-pipeline`
- **Run Daemon**: `poetry run python daemon.py`
- **Vector Scatterplot**: `poetry run python visualize.py`

### Tox Automation Targets
- **Run All Test Envs**: `tox` or `tox -r`
- **Unit Tests**: `tox -e pytest`
- **Linting**: `tox -e lint`
- **Format Verification**: `tox -e format`
- **Type Checking**: `tox -e typecheck`
- **Build Distribution & Zip**: `tox -e dist` (produces `babylon-features.zip` and `dist/` wheels)

---

## Clean & Comprehensive Coding Patterns

All Python code written for `babylon_features` must prioritize maintainability, test economy, and low cognitive load:

1. **Function Decomposition & Single Responsibility**:
   - Break large procedures into cohesive private helpers with explicit parameter types and return annotations.
2. **Low Cognitive Complexity**:
   - Keep control flow flat; use early returns and guard clauses instead of deeply nested `if/else` blocks.
3. **Test Boilerplate Elimination & Domain Builders**:
   - In unit tests, eliminate repetitive dictionary and model construction using domain builder helpers:
     ```python
     def new_valid_dto(**overrides: Any) -> TransactionDto:
         payload = {
             "record_id": "tx-12345",
             "amount": 42.50,
             "posting_date": date(2023, 1, 15),
             "details": "grocery purchase",
             "tx_type": "DEBIT",
             "description": "Supermarket Store #42",
             "check_num": "001",
         }
         payload.update(overrides)
         return TransactionDto(**payload)
     ```
4. **Declarative Table-Driven Tests**:
   - Use `@pytest.mark.parametrize` with explicit test IDs, verifying single invariants per test case.
5. **Hermetic Test Isolation**:
   - Unit tests must never connect to live MongoDB clusters, ChromaDB disks, or Qdrant endpoints; use mocks (`unittest.mock.MagicMock`, `pytest.fixture`).
6. **Exception Boundary Encapsulation**:
   - Driver-level exceptions (`bson.errors.InvalidId`, `pymongo.errors.*`, `qdrant_client.http.exceptions.*`) must never leak past domain interfaces. Map or handle them at repository and vector store boundaries.

---

## Security & PII Guidelines

1. **Zero Real PII**:
   - Never commit, mock, or log real financial transaction records, account numbers, card numbers, or customer identity information.
2. **Log Safety & Sanitization**:
   - Logs must only contain aggregate metrics (e.g., `batch_number`, `chunks_emitted`, elapsed time) and sanitized non-sensitive IDs. Never print transaction descriptions, amounts, or account details.
3. **Synthetic Data for Development**:
   - Always rely on synthetic test fixtures generated programmatically via domain builders or mock generators.
4. **Credential Isolation & OpenBao**:
   - Never hardcode credentials, passwords, or connection URIs.
   - Database credentials must be retrieved dynamically from OpenBao (`BaoSecretsManager`) or injected via environment variables (`.env`).

---

## Babylon 2.0 Governance

Agents operating in `babylon_features` must strictly observe Babylon 2.0 global governance rules:

1. **Planning First & Proactive Decomposition**:
   - Always formulate and present a comprehensive implementation plan before making modifications.
   - **Floor (Anti-Microphasing)**: Roll minor changes (< 150 lines diff) into subsequent phases.
   - **Ceiling (Max PR Size)**: Bound every phase/PR to Medium effort (150–600 lines total diff including tests, 1–3 files, single domain).
   - **Mandatory Decomposition**: If work spans multiple adapters or exceeds 600 lines (accounting for the 2.5x test multiplier), proactively decompose into numbered sub-phases (e.g., Phase 2A, Phase 2B).
2. **Spec-First Engineering**:
   - Ensure all changes align with technical specifications in `docs/specs/`. Run local quality gates (`poetry run black`, `poetry run pylint`, `poetry run pytest`) before handing off work.
3. **Path Portability Rule**:
   - Documentation, specifications, docstrings, and tests must **NEVER** contain personal or home directory paths (`/Users/`, `/home/`, `~`). Use repository-relative paths only.
4. **Zero-Secret Tolerance**:
   - Never commit secrets, tokens, or private credentials.
5. **Strict Pull Request Merge Restriction**:
   - Agents must **NEVER** merge pull requests (`gh pr merge`, GitHub API merges, or direct branch merges into `main`) on the user's behalf without explicit, unambiguous permission.
   - Report the PR link, test verification, and hand off for human review.
6. **Mandatory Verification & Documentation Update Gate**:
   - Before completing tasks, opening PRs, or handing off work, agents **MUST** execute `make verify` (or `./scripts/verify.sh`).
   - Every code modification in `features/` must be evaluated against the canonical specifications in `docs/specs/` and accompanied by appropriate documentation updates. Stale specifications are strictly prohibited.
