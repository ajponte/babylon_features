from unittest.mock import patch, MagicMock
from features.pipeline.generate_features import generate_features

def test_generate_features_flow():
    with patch("features.pipeline.generate_features.fg_steps") as mock_fg_steps:
        # Mocking return values for steps.
        # ZenML steps return a StepInvocation or similar,
        # but if we mock them, they return whatever we set.

        mock_raw = MagicMock(invocation_id="raw_docs_id")
        mock_clean = MagicMock(invocation_id="clean_docs_id")
        mock_step1 = MagicMock(invocation_id="step1_id")
        mock_embedded = MagicMock(invocation_id="embedded_id")
        mock_step2 = MagicMock(invocation_id="step2_id")

        mock_fg_steps.query_data_lake.return_value = mock_raw
        mock_fg_steps.clean_documents.return_value = mock_clean
        mock_fg_steps.load_to_vector_db.side_effect = [mock_step1, mock_step2]
        mock_fg_steps.chunk_and_embed.return_value = mock_embedded

        # Call the pipeline's entrypoint directly to bypass ZenML orchestration overhead
        result = generate_features.entrypoint(wait_for="some_step")

        # Verify calls
        mock_fg_steps.query_data_lake.assert_called_once_with(after="some_step")
        mock_fg_steps.clean_documents.assert_called_once_with(mock_raw)

        # load_to_vector_db is called twice
        assert mock_fg_steps.load_to_vector_db.call_count == 2
        mock_fg_steps.load_to_vector_db.assert_any_call(mock_clean)
        mock_fg_steps.load_to_vector_db.assert_any_call(mock_embedded)

        mock_fg_steps.chunk_and_embed.assert_called_once_with(mock_clean)

        assert result == ["step1_id", "step2_id"]

def test_generate_features_multiple_wait_for():
    with patch("features.pipeline.generate_features.fg_steps") as mock_fg_steps:
        mock_raw = MagicMock(name="raw_docs_invocation")
        mock_clean = MagicMock(name="clean_docs_invocation")
        mock_step1 = MagicMock(name="step1_invocation", invocation_id="step1_id")
        mock_embedded = MagicMock(name="embedded_invocation")
        mock_step2 = MagicMock(name="step2_invocation", invocation_id="step2_id")

        mock_fg_steps.query_data_lake.return_value = mock_raw
        mock_fg_steps.clean_documents.return_value = mock_clean
        mock_fg_steps.load_to_vector_db.side_effect = [mock_step1, mock_step2]
        mock_fg_steps.chunk_and_embed.return_value = mock_embedded

        # Call with multiple wait_for items
        wait_list = ["step_a", "step_b"]
        result = generate_features.entrypoint(wait_for=wait_list)

        mock_fg_steps.query_data_lake.assert_called_once_with(after=wait_list)
        assert result == ["step1_id", "step2_id"]
