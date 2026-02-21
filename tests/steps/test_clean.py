from features_pipeline.steps.feature_generation.clean import clean_documents

def test_clean_documents():
    """Test the clean_documents step."""
    raw_docs = [{"id": 1, "text": "raw"}]
    # Current implementation returns empty list (todo)
    result = clean_documents.entrypoint(documents=raw_docs)
    assert result == []
