from features.steps.feature_generation.query_data_lake import query_data_lake

def test_query_data_lake():
    """Test the query_data_lake step."""
    descriptions = ["trans 1", "trans 2"]
    # Current implementation returns empty list (todo)
    result = query_data_lake.entrypoint(transaction_descriptions=descriptions)
    assert result == []
