from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum

from zenml import step

from typing_extensions import Annotated

from features.domain.cleaned_documents import (
    CleanedDocument,
    CleanedTransactionDocument,
)
from features.logger import get_logger

_LOGGER = get_logger()


class Feature(Enum):
    """Represents a feature this pipeline can produce."""

    TRANSACTIONS = "transactions"
    # todo
    ARTICLES = "articles"
    MARKET_SNAPSHOT = "market-snapshot"


@step
def query_feature_store() -> Annotated[list, "queried_cleaned_documents"]:
    _LOGGER.info("Querying feature store.")
    results = fetch_all_data()
    cleaned_documents = [
        doc for query_result in results.values() for doc in query_result
    ]

    return cleaned_documents


def fetch_all_data() -> dict[str, list]:
    """Fetch all requisite data from the vector db."""
    with ThreadPoolExecutor() as executor:
        # todo: Add more as needed.
        query_futures = {
            executor.submit(__fetch_transactions): "transactions",
            executor.submit(__fetch_articles): "articles",
        }

        results = {}
        for future in as_completed(query_futures):
            query_name = query_futures[future]
            try:
                results[query_name] = future.result()
            except Exception:
                _LOGGER.debug(f"'{query_name}' request failed.")
                results[query_name] = []

    return results


def __fetch_transactions() -> list[CleanedDocument]:
    """Fetch cleaned transaction documents from the Vector DB."""
    return __fetch(CleanedTransactionDocument)


def __fetch_articles() -> list[CleanedDocument]:
    """Fetch cleaned article documents from the Vector DB."""
    # todo
    return []


def __fetch(
    cleaned_document_type: type[CleanedDocument], limit: int = 1
) -> list[CleanedDocument]:
    """Fetch cleaned documents for the type."""
    try:
        cleaned_documents, next_offset = cleaned_document_type.bulk_find(limit=limit)
    except Exception as e:
        _LOGGER.debug(
            f"Encountered exception while fetching cleaned documents. Error: {e}"
        )
        return []

    while next_offset:
        documents, next_offset = cleaned_document_type.bulk_find(
            limit=limit, offset=next_offset
        )
        cleaned_documents.extend(documents)

    return cleaned_documents
