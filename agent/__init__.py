"""
An Agent Harness is software infrastructure which wraps around an LLM, in order to
enable long-running agent sessions through managing the lifecycle of an active context.

It acts as a control layer providing task planning, memory, and human-in-the-loop oversight.
In a sense, an agent harness transforms a specialized model into a slightly specialized
autonomous agent.

For more information, see https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
"""
