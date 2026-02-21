from features_pipeline.steps.feature_generation.load_vectors import load_to_vector_db

def test_load_to_vector_db():
    """Test the load_to_vector_db step."""
    docs = [{"id": 1, "vector": [0.1, 0.2]}]
    # Current implementation returns True (todo)
    result = load_to_vector_db.entrypoint(documents=docs)
    assert result is True
