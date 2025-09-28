#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "google-adk",
#     "litellm",
# ]
# ///

# uv add --script=sample.py "google-adk"
# uv add --script=sample.py "litellm"
"""
A simple Google ADK agent that uses an OpenAI model as its backend.
This script requires the OPENAI_API_KEY environment variable to be set.
"""
import os
import asyncio
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

async def main():
    """
    Sets up and runs an ADK agent with an OpenAI backend to answer a question.
    """
    print("🚀 Initializing agent with OpenAI backend...")

    # 1. Verify the OpenAI API key is available in the environment.
    # The LiteLLM library will automatically pick up this environment variable.
    if "OPENAI_API_KEY" not in os.environ:
        raise ValueError(
            "🛑 The OPENAI_API_KEY environment variable is not set. "
            "Please set it before running the script."
        )

    # 2. Configure the LLM to use an OpenAI model via LiteLLM.
    # We are using "openai/gpt-4o" here, but you can change it to another model like "openai/gpt-4-turbo".
    try:
        llm = LiteLlm(model="openai/gpt-4o")
        print(f"✅ LLM configured to use model: {llm.model}")
    except Exception as e:
        print(f"🔥 Failed to initialize LLM: {e}")
        return

    # 3. Create the agent instance, passing in our configured LLM.
    agent = LlmAgent(
        model=llm,
        name="openai_agent",
        instruction="You are a helpful assistant powered by GPT-4o."
    )
    print("🤖 Agent created successfully.")

    # 4. Setup session and runner
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="openai_adk_app",
        user_id="user_1",
        session_id="session_1"
    )

    runner = Runner(
        agent=agent,
        app_name="openai_adk_app",
        session_service=session_service
    )

    # 5. Define the question and run the agent.
    question = "what is best in life?"
    print(f"\n💬 Asking the agent: '{question}'")
    print("⏳ Waiting for response...")

    try:
        await call_agent_async(runner, question)
    except Exception as e:
        print(f"🔥 An error occurred while running the agent: {e}")

async def call_agent_async(runner: Runner, query: str):
    """Sends a query to the agent and prints the final response."""
    content = types.Content(role='user', parts=[types.Part(text=query)])
    final_response_text = "Agent did not produce a final response."

    async for event in runner.run_async(
        user_id="user_1",
        session_id="session_1",
        new_message=content
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
                break

    # Print the final response from the agent.
    print("\n" + "="*30)
    print("💡 Agent's Response:")
    print(final_response_text)
    print("="*30)


if __name__ == "__main__":
    asyncio.run(main())
