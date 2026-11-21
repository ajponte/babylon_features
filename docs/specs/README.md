# Babylon Features & Embedding Pipeline Architecture Catalog & Specification Suite

This catalog indexes the canonical architectural specifications for the feature engineering, datalake extraction, document chunking, and vector embedding pipelines within the `babylon_features` subsystem. The specifications define the technical contracts governing data transformation, persistence boundaries, error handling, and vector store integration across the Babylon 2.0 financial platform.

---

## 1. Architectural Document Catalog

| Document | Primary Package / Scope | Key Architectural Invariants & Topics |
| :--- | :--- | :--- |
| **[Datalake Storage & Repository Specification](./datalake-storage-repository.md)** | `features/datalake/`<br>`tests/datalake/` | Domain transfer objects (`TransactionDto`), query limit validation (`_apply_limit`), defensive repository query seams (`BaseRepository`, `TransactionRepository`), ObjectId validation boundaries, null-safe iterators, driver exception encapsulation. |
| **[Vectorization & Processing Pipeline Specification](./vectorization-processing-pipeline.md)** | `features/processor.py`<br>`features/vectorstore/`<br>`features/rag/` | Batch chunking lifecycle (`CollectionProcessor`), recursive text splitting (`RecursiveCharacterTextSplitter`), multi-backend vector store abstraction (`ChromaVectorStore`, `QdrantVectorStore`), fault-tolerant document building, CLI vectorization harness (`poetry run vectorize`). |

---

## 2. End-to-End Architecture & Subsystem Data Flow

The `babylon_features` pipeline acts as the analytical bridge between raw bank statement ingestion in the MongoDB datalake and downstream Retrieval-Augmented Generation (RAG) agents:

```mermaid
flowchart TD
    subgraph DatalakePersistence ["MongoDB Datalake Layer (Read-Only)"]
        MONGO_DB[("MongoDB Atlas / Datalake<br/>• transactions_* collections")]
        FACTORY["MongoClientFactory<br/>(features/datalake/mongo_factory.py)"]
        UOW["UnitOfWork Session<br/>(features/datalake/uow.py)"]
        MONGO_DB -.->|connection| FACTORY
        FACTORY -->|sessions| UOW
    end

    subgraph RepositoryDomain ["Repository & Domain Contract Layer"]
        BASE_REPO["BaseRepository<br/>(features/datalake/repository.py)<br/>• _apply_limit(cursor, limit)<br/>• get_by_id(_id)<br/>• get_all(limit)<br/>• get_by_filter(filter, limit)"]
        TX_REPO["TransactionRepository<br/>(features/datalake/repository.py)"]
        MAPPER["TransactionMapper<br/>(features/datalake/repository.py)"]
        DTO["TransactionDto<br/>• id, amount, posting_date<br/>• description, details, type, check_num"]

        UOW -->|collection| TX_REPO
        TX_REPO --|>|inherits| BASE_REPO
        BASE_REPO -->|delegates mapping| MAPPER
        MAPPER -->|instantiates| DTO
    end

    subgraph FeaturePipeline ["Document Building & Chunking Pipeline"]
        PROC["CollectionProcessor<br/>(features/processor.py)<br/>• process(mongo_repository)<br/>• batch_number tracking"]
        DOC_BUILDER["Document Builder<br/>(features/rag/documents/document_builder.py)<br/>• build_langchain_document(source, coll)"]
        SPLITTER["RecursiveCharacterTextSplitter<br/>• chunk_size: 1000<br/>• chunk_overlap: 100"]

        DTO -->|read into| PROC
        PROC -->|converts via| DOC_BUILDER
        DOC_BUILDER -->|yields LangChain Document| SPLITTER
        SPLITTER -->|splits into chunks| CHUNKS["list[Document] (Chunks)"]
    end

    subgraph VectorPersistence ["Vector Storage Layer (Write/Query)"]
        FACTORY_VEC["vector_store_factory(config)<br/>(features/vectorstore/vectorstore.py)"]
        VEC_STORE["VectorStore (Port / ABC)<br/>• add_documents(documents)<br/>• similarity_search(query, top_k)<br/>• get_all(limit)"]
        CHROMA["ChromaVectorStore<br/>(langchain-chroma / SQLite)"]
        QDRANT["QdrantVectorStore<br/>(langchain-qdrant / REST & gRPC)"]

        FACTORY_VEC -->|instantiates| VEC_STORE
        CHROMA --|>|implements| VEC_STORE
        QDRANT --|>|implements| VEC_STORE
        CHUNKS -->|persisted via add_documents| VEC_STORE
    end
```

---

## 3. Cross-Cutting Architectural Invariants

Across the `babylon_features` pipeline, five core invariants are strictly enforced:

### 3.1 Driver Exception Encapsulation
PyMongo and BSON driver-level exceptions (such as `bson.errors.InvalidId`, `pymongo.errors.ServerSelectionTimeoutError`, and `AutoReconnect`) must never leak past the datalake repository boundary.
- Document lookup with malformed or unparseable IDs must be intercepted by `BaseRepository.get_by_id` and return `None` rather than raising driver exceptions.
- Similarly, downstream vector store driver exceptions are wrapped into unified domain exceptions (`features.error.VectorDBError`).

### 3.2 Strict Type Guarding
Query boundaries strictly validate and enforce parameter types before delegating calls to underlying database drivers:
- The `limit` parameter across `BaseRepository.get_all`, `BaseRepository.get_by_filter`, and `_apply_limit` strictly rejects boolean values (`True`, `False`) and non-integer numbers with a `TypeError`.
- Non-positive integer values (`limit <= 0`) are rejected with a descriptive `ValueError`.

### 3.3 Datalake Read-Only Invariant
The `babylon_features` subsystem operates in strictly **read-only** mode against the primary MongoDB datalake.
- Transaction records are extracted, normalized into domain transfer objects, and chunked for embeddings.
- No write, update, upsert, or deletion operations are permitted against financial transaction collections by this pipeline.

### 3.4 Fault Domain Isolation
Ingestion failures and external service outages must remain isolated to their respective fault domains:
- Vector database latency spikes, connection drops, or schema rejections must never abort, corrupt, or block upstream datalake ingestion workflows.
- During document chunking and metadata building within `CollectionProcessor`, a failure on a single malformed transaction is logged and skipped, guaranteeing that remaining batch records continue processing uninterrupted.

### 3.5 PII & Path Portability
All architectural documents, codebases, and generated metadata artifacts must strictly adhere to environment-agnostic relative paths:
- Absolute personal, user, or home workspace directory paths are strictly prohibited in all committed markdown, docstrings, and tests.
- High-entropy secrets, database credentials, Vault tokens, and raw PII are strictly excluded from logging statements and vector metadata attributes.

---

## 4. Subsystem Directory Structure

```text
babylon_features/
├── docs/specs/
│   ├── README.md                               # This document (Master Architecture Catalog)
│   ├── datalake-storage-repository.md          # Specification: Datalake Repository & Domain Contracts
│   └── vectorization-processing-pipeline.md    # Specification: Vector Store & Processing Pipeline
├── features/
│   ├── config/                                 # Configuration loaders & HashiCorp Vault / OpenBao client
│   ├── datalake/
│   │   ├── mongo_factory.py                    # MongoClient connection factory
│   │   ├── repository.py                       # TransactionDto, BaseRepository, TransactionRepository
│   │   └── uow.py                              # UnitOfWork MongoDB session context manager
│   ├── processor.py                            # DataLakeProcessor & CollectionProcessor
│   ├── rag/
│   │   └── documents/
│   │       └── document_builder.py             # LangChain Document & metadata builder
│   ├── vectorstore/
│   │   └── vectorstore.py                      # VectorStore abstraction, ChromaDB & Qdrant adapters
│   └── logger.py                               # Structured logger configuration
└── tests/
    ├── datalake/
    │   └── test_repository.py                 # Declarative table-driven tests for repository layer
    ├── rag/documents/                          # Document builder test harness
    └── test_processor.py                       # Processor batch lifecycle and fault-isolation tests
```
