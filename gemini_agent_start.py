from agent.event import EventType
from agent.gemini.event import GeminiEventManager
from agent.gemini_agent import GeminiAgent
from agent.utils import get_now

DEFAULT_CONFIG = {
    'agent': {
        'llm_model': 'gemini',
        'enable_automatic_function_calling': True
    }
}

# Temporary for testing.
get_weather = lambda location: f"The weather in {location} is currently 72°F and sunny."
multiply_numbers = lambda a,b: a * b

DEFAULT_AGENT_TOOLS = [
    get_weather,
    multiply_numbers
]



if __name__ == '__main__':
    user_input = "What's the weather in San Francisco, and what is 1234 times 56?"
    print('Starting new agent.')
    gemini = GeminiAgent(config=DEFAULT_CONFIG, tools=DEFAULT_AGENT_TOOLS)
    response = gemini.chat(prompt=user_input)
