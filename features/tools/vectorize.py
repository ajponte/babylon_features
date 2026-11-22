"""Standalone CLI tool to vectorize MongoDB datalake records into vector databases."""

from dataclasses import dataclass
import os
import time
from typing import Any

import click
from langchain_core.documents import Document

from features.config.config import update_config_from_environment
from features.datalake.mongo_factory import MongoClientFactory
from features.datalake.repository import TransactionRepository
from features.logger import get_logger
from features.processor import chunk_transactions
from features.vectorstore.vectorstore import VectorStore, vector_store_factory

_LOGGER = get_logger()

COLLECTIONS: tuple[str, ...] = ("transactions_chase", "transactions_synthetic")


@dataclass
class VectorizeSummary:
    """Telemetry execution summary."""

    collections: list[str]
    limit: int | None
    documents_fetched: int
    chunks_generated: int
    vector_db: str
    dry_run: bool
    elapsed_seconds: float

    def render(self) -> str:
        """Format the execution summary telemetry block."""
        lines = [
            "=" * 60,
            "Vectorization Execution Summary",
            "=" * 60,
            f"Target Collection(s) : {', '.join(self.collections)}",
            f"Record Limit Applied : {self._format_limit()}",
            f"Documents Fetched    : {self.documents_fetched}",
            f"Chunks Generated     : {self.chunks_generated}",
            f"Vector Store Backend : {self._format_backend()}",
            f"Dry Run Mode         : {self._format_dry_run()}",
            f"Elapsed Time         : {self.elapsed_seconds:.2f}s",
            "=" * 60,
        ]
        return "\n".join(lines)

    def _format_limit(self) -> str:
        if self.limit is not None:
            return str(self.limit)
        return "None (All)"

    def _format_backend(self) -> str:
        if self.vector_db.lower() == "chroma":
            return "ChromaDB (Persistent)"
        if self.vector_db.lower() == "qdrant":
            return "Qdrant (Cluster)"
        return self.vector_db

    def _format_dry_run(self) -> str:
        if self.dry_run:
            return "True (No writes performed)"
        return "False (Persisted successfully)"


def resolve_collections(name: str) -> list[str]:
    """Resolve target collection names.

    'all' (case-insensitive) returns COLLECTIONS. Known collection names
    are case-sensitive matching MongoDB collection namespaces.
    Anything else raises ValueError.

    :param name: Specified collection name or 'all'.
    :return: List of collection names.
    :raises ValueError: If the collection name is unknown.
    """
    cleaned = name.strip()
    if cleaned.lower() == "all":
        return list(COLLECTIONS)
    if cleaned in COLLECTIONS:
        return [cleaned]
    raise ValueError(
        f"Unknown collection '{name}'. Available collections: {', '.join(COLLECTIONS)}"
    )


def resolve_repositories(
    collection_names: list[str],
) -> list[tuple[str, TransactionRepository]]:
    """Build a TransactionRepository per collection with environment fallbacks.

    :param collection_names: List of datalake collection names.
    :return: List of (collection_name, TransactionRepository) pairs.
    """
    cfg: dict[str, Any] = {
        "MONGO_DATA_LAKE_NAME": os.environ.get("MONGO_DATA_LAKE_NAME", "datalake"),
        "MONGO_DB_HOST": os.environ.get("MONGO_DB_HOST", "localhost"),
        "MONGO_DB_PORT": int(os.environ.get("MONGO_DB_PORT", "27017")),
        "MONGO_DB_USER": os.environ.get("MONGO_DB_USER", "babylon"),
        "MONGO_DB_PASSWORD": os.environ.get("MONGO_DB_PASSWORD", "babylonpass"),
        "MONGO_CONNECTION_TIMEOUT_SECONDS": int(
            os.environ.get("MONGO_CONNECTION_TIMEOUT_SECONDS", "30")
        ),
    }
    if "MONGO_URI" in os.environ:
        cfg["MONGO_URI"] = os.environ["MONGO_URI"]

    try:
        update_config_from_environment(cfg)
    except Exception as err:
        _LOGGER.debug("Failed loading environment config: %s", err)

    db_name = cfg.get("MONGO_DATA_LAKE_NAME", "datalake")
    client = MongoClientFactory.get_client(config=cfg)

    repositories: list[tuple[str, TransactionRepository]] = []
    for name in collection_names:
        coll = MongoClientFactory.get_collection(
            db_name=db_name, coll_name=name, client=client
        )
        repositories.append((name, TransactionRepository(coll)))
    return repositories


def build_store(vector_db: str) -> VectorStore:
    """Return ChromaVectorStore or QdrantVectorStore from features config.

    Only called when not dry-run (P2-D4).

    :param vector_db: Name of target vector database ('chroma' or 'qdrant').
    :return: Configured VectorStore instance.
    """
    cfg: dict[str, Any] = {
        "VECTOR_DB_TYPE": vector_db.lower(),
        "EMBEDDING_MODEL": os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"),
        "CHROMA_SQLITE_DIR": os.environ.get("CHROMA_SQLITE_DIR", "./chromadb"),
        "EMBEDDINGS_COLLECTION_CHROMA": os.environ.get(
            "EMBEDDINGS_COLLECTION_CHROMA", "babylon_vectors"
        ),
        "QDRANT_HOST": os.environ.get("QDRANT_HOST", "localhost"),
        "QDRANT_PORT": int(os.environ.get("QDRANT_PORT", "6333")),
        "QDRANT_COLLECTION": os.environ.get("QDRANT_COLLECTION", "babylon_vectors"),
    }
    try:
        update_config_from_environment(cfg)
        cfg["VECTOR_DB_TYPE"] = vector_db.lower()
    except Exception as err:
        _LOGGER.debug("Failed updating config from environment: %s", err)

    return vector_store_factory(cfg)


def validate_chunking(chunk_size: int, chunk_overlap: int) -> None:
    """Raise click.BadParameter unless 0 <= chunk_overlap < chunk_size (P2-D5).

    :param chunk_size: Maximum characters per chunk.
    :param chunk_overlap: Overlapping character count.
    :raises click.BadParameter: If parameters violate chunking boundaries.
    """
    if (
        isinstance(chunk_size, bool)
        or not isinstance(chunk_size, int)
        or chunk_size <= 0
    ):
        raise click.BadParameter(
            f"chunk_size must be a positive integer, got {chunk_size}",
            param_hint="--chunk-size",
        )
    if (
        isinstance(chunk_overlap, bool)
        or not isinstance(chunk_overlap, int)
        or chunk_overlap < 0
    ):
        raise click.BadParameter(
            f"chunk_overlap must be a non-negative integer, got {chunk_overlap}",
            param_hint="--chunk-overlap",
        )
    if chunk_overlap >= chunk_size:
        raise click.BadParameter(
            f"chunk_overlap ({chunk_overlap}) must be strictly less than chunk_size ({chunk_size})",
            param_hint="--chunk-overlap",
        )


def _extract_and_chunk_repositories(
    repositories: list[tuple[str, TransactionRepository]],
    limit: int | None,
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[int, list[Document]]:
    """Fetch transactions and generate LangChain chunks across repositories."""
    total_fetched = 0
    all_chunks: list[Document] = []
    for name, repo in repositories:
        records = repo.get_by_filter({}, limit=limit)
        total_fetched += len(records)
        chunks = chunk_transactions(
            records,
            collection_name=name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        all_chunks.extend(chunks)
    return total_fetched, all_chunks


def _persist_chunks(vector_db: str, chunks: list[Document], dry_run: bool) -> None:
    """Persist chunks to vector store unless running in dry-run mode."""
    if not dry_run and chunks:
        store = build_store(vector_db)
        store.add_documents(chunks)


# pylint: disable=too-many-arguments,too-many-positional-arguments
@click.command(help="Vectorize MongoDB datalake records into ChromaDB or Qdrant.")
@click.option(
    "-c",
    "--collection",
    default="all",
    help="Target collection name or 'all' for all configured collections.",
)
@click.option(
    "-l",
    "--limit",
    type=click.IntRange(min=1),
    default=None,
    help="Maximum number of records to fetch per collection.",
)
@click.option(
    "-v",
    "--vector-db",
    type=click.Choice(["chroma", "qdrant"], case_sensitive=False),
    default="chroma",
    help="Target vector database backend.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Perform discovery, extraction, and chunking without writing to vector database.",
)
@click.option(
    "--chunk-size",
    type=click.IntRange(min=1),
    default=1000,
    help="Maximum characters per chunk.",
)
@click.option(
    "--chunk-overlap",
    type=click.IntRange(min=0),
    default=100,
    help="Character overlap between consecutive chunks.",
)
def main(
    collection: str,
    limit: int | None,
    vector_db: str,
    dry_run: bool,
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    """Vectorize MongoDB datalake records into ChromaDB or Qdrant."""
    validate_chunking(chunk_size, chunk_overlap)

    try:
        collection_names = resolve_collections(collection)
    except ValueError as err:
        raise click.BadParameter(str(err), param_hint="--collection") from err

    start_time = time.perf_counter()
    try:
        repositories = resolve_repositories(collection_names)
        total_fetched, all_chunks = _extract_and_chunk_repositories(
            repositories, limit, chunk_size, chunk_overlap
        )
    except click.ClickException:
        raise
    except Exception as err:
        _LOGGER.error("Datalake extraction failed: %s", err, exc_info=True)
        raise click.ClickException(f"Datalake extraction failed: {err}") from err

    _persist_chunks(vector_db, all_chunks, dry_run)
    elapsed = time.perf_counter() - start_time

    summary = VectorizeSummary(
        collections=collection_names,
        limit=limit,
        documents_fetched=total_fetched,
        chunks_generated=len(all_chunks),
        vector_db=vector_db,
        dry_run=dry_run,
        elapsed_seconds=elapsed,
    )
    click.echo(summary.render())
