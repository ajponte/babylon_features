from pytest import fixture

from datalake.repository import TransactionDto, TransactionMapper
from features_pipeline.rag.documents.document_builder import build_document_metadata, build_langchain_document

MOCK_DATALAKE_COLLECTION_NAME = 'test-dl-record'
MOCK_DATALAKE_RECORD_ID = '68eb41eca6ecff590db124a1'
MOCK_POSTING_DATE = "01/31/2023"
MOCK_DESCRIPTION = "WHOLEFDS HAR 102 230 B OAKLAND CA    211023  01/31"
MOCK_DETAILS = "extra details"
MOCK_AMOUNT = -75.77
MOCK_TRANSACTION_TYPE = "DEBIT_CARD"

MOCK_DATALAKE_RECORD = {
    "_id": MOCK_DATALAKE_RECORD_ID,
    "PostingDate": MOCK_POSTING_DATE,
    "Description": MOCK_DESCRIPTION,
    "Details": MOCK_DETAILS,
    "Amount": MOCK_AMOUNT,
    "Type": MOCK_TRANSACTION_TYPE
}

@fixture
def source_record() -> TransactionDto:
    """Return a mock source record from the datalake."""
    return TransactionMapper.to_domain(MOCK_DATALAKE_RECORD)

def test_build_langchain_document(source_record):
    result = build_langchain_document(
        source=source_record,
        collection=MOCK_DATALAKE_COLLECTION_NAME
    )

    data = result.to_json()
    # Test the source record cached in metadata
    metadata = data['kwargs']['metadata']
    assert metadata['source_collection'] == MOCK_DATALAKE_COLLECTION_NAME
    assert metadata['source_document_id'] == MOCK_DATALAKE_RECORD_ID
