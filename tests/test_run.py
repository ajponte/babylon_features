import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from click.testing import CliRunner

# Add the project root to sys.path if needed
sys.path.append(str(Path(__file__).resolve().parent.parent))

from features.tools.run import main

def test_main_help():
    """Test that the help message is displayed."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Babylon RAG Pipeline." in result.output

@patch("features.tools.run.dotenv.load_dotenv")
@patch("features.tools.run.config.update_config_from_environment")
@patch("features.tools.run.generate_features")
def test_main_run_feature_engineering(mock_generate_features, mock_update_config, mock_load_dotenv):
    """Test that run_feature_engineering calls the pipeline with expected config."""
    # Setup mocks
    mock_pipeline_with_options = MagicMock()
    mock_generate_features.with_options.return_value = mock_pipeline_with_options
    
    # We need to simulate that some env vars are found and populated into run_args_fe
    def side_effect(config_dict):
        config_dict["MOCK_CONFIG"] = "MOCK_VALUE"
    mock_update_config.side_effect = side_effect

    runner = CliRunner()
    # We need to pass --run-feature-engineering
    result = runner.invoke(main, ["--run-feature-engineering"])
    
    # Assertions
    assert result.exit_code == 0
    
    # Check if load_dotenv was called (assuming .env might exist in test environment or we mock it)
    # Even if it doesn't exist, we check if it was attempted.
    assert mock_load_dotenv.called
    
    # Check if generate_features.with_options was called
    assert mock_generate_features.with_options.called
    options_call_args = mock_generate_features.with_options.call_args[1]
    assert "config_path" in options_call_args
    assert "feature_engineering.yaml" in str(options_call_args["config_path"])
    
    # Check if the pipeline was invoked with run_args_fe
    mock_pipeline_with_options.assert_called_once()
    invocation_args = mock_pipeline_with_options.call_args[1]
    assert invocation_args["MOCK_CONFIG"] == "MOCK_VALUE"

def test_main_no_action():
    """Test that main shows an error if no action is specified."""
    runner = CliRunner()
    result = runner.invoke(main, [])
    # In the updated run.py, it logs an error and returns instead of asserting
    # logger.error("Please specify an action to run.")
    assert "Please specify an action to run." in result.output
