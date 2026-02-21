from features.steps.feature_generation.chunk_and_embed import chunk_and_embed

def test_chunk_and_embed():
    """Test the chunk_and_embed step."""
    docs = [{"id": 1, "text": "cleaned content"}]
    # Current implementation returns empty list (todo)
    result = chunk_and_embed.entrypoint(cleaned_documents=docs)
    assert result == []
