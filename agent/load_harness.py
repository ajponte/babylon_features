from typing import Mapping, Any

from agent.agent_harness import AgentHarness


def load_harness(config: Mapping[str, Any]) -> AgentHarness:
    harness = None
    agent_config = config.get('agent')
    if not agent_config:
        raise ValueError('No agent passed to config')
    if agent_config['llm_model'] == 'gemini':
        harness = load_harness(agent_config)

    return harness
