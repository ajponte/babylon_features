from typing import Callable, Any
from .harness import GeminiAgentHarness

def load_harness(
    config: dict[str, Any],
    tools: list[Callable] | None = None,
    agent_id: str | None = None,
    api_key: str | None = None
) -> GeminiAgentHarness:
    model: str = config['agent']['llm_model']
    return GeminiAgentHarness(
        model_name=model,
        tools=tools,
        agent_id=agent_id,
        api_key=api_key
    )
