from typing import Mapping, Any

from agent.agent_harness import AgentHarness
from agent.gemini.load import load_harness as load_gemini_harness


def load_harness(config: Mapping[str, Any]) -> AgentHarness:
    harness = None
    agent_config = config.get('agent')
    if not agent_config:
        raise ValueError('No agent passed to config')
    if agent_config['llm_model'] == 'gemini':
        harness = load_gemini_harness(agent_config)

    return harness
