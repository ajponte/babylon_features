import google.generativeai as genai
import os

# Configure your API key
genai.configure(api_key="YOUR_GEMINI_API_KEY")

# 1. Define your tools
def get_weather(location: str):
    # In a real app, this would call an external API
    return f"The weather in {location} is currently 72°F and sunny."

def multiply_numbers(a: float, b: float):
    return a * b

# 2. Initialize the model with tools
# The 'tools' parameter tells Gemini what it is allowed to call
model = genai.GenerativeModel(
    model_name='gemini-1.5-pro',
    tools=[get_weather, multiply_numbers]
)

# 3. Start a chat session with automatic function calling enabled
# 'enable_automatic_function_calling=True' handles the loop for you
chat = model.start_chat(enable_automatic_function_calling=True)

def run_agent(prompt: str):
    response = chat.send_message(prompt)
    return response.text

# Example Usage
if __name__ == "__main__":
    user_input = "What's the weather in San Francisco, and what is 1234 times 56?"
    result = run_agent(user_input)
    print(result)
