#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "google-adk",
#     "litellm",
# ]
# ///
"""
An ADK agent that uses an OpenAI model and connects to a remote tool
server (MCP) using Server-Sent Events (SSE).
"""
import os
import asyncio
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.tools.mcp_tool import McpToolset

# Import the SSE connection parameters from the ADK
from google.adk.tools.mcp_tool import SseConnectionParams

# URL for the MCP server. Ensure mcp_server.py is running on this address.
MCP_SERVER_URL = "http://localhost:8775/sse"

def create_mcp_tools_sse():
    """Create MCP tools by connecting to the mcp_server.py via SSE."""
    print(f"Attempting to connect to MCP tool server via SSE at {MCP_SERVER_URL}...")
    try:
        # Create a toolset that connects to the server using SSE
        toolset = McpToolset(
            connection_params=SseConnectionParams(url=MCP_SERVER_URL)
        )
        print("✅ Successfully connected to MCP tool server.")
        return [toolset]
    except Exception as e:
        print(f"🔥 Warning: Failed to connect to MCP server via SSE: {e}")
        print("👉 Please ensure the mcp_server.py is running in a separate terminal.")
        return []

async def main():
    """
    Sets up and runs the agent with OpenAI and remote SSE tools.
    """
    print("🚀 Initializing Cases AI Agent...")

    # 1. Verify the OpenAI API key is available in the environment.
    if "OPENAI_API_KEY" not in os.environ:
        raise ValueError("🛑 The OPENAI_API_KEY environment variable is not set.")

    # 2. Configure the LLM to use an OpenAI model via LiteLLM.
    llm = LiteLlm(model="openai/gpt-4o")
    print(f"✅ LLM configured to use model: {llm.model}")

    # 3. Create the toolset by connecting to the running MCP server.
    mcp_tools = create_mcp_tools_sse()
    if not mcp_tools:
        print(" Agent initialization failed. Exiting.")
        return

    # 4. Create the root agent with your detailed instructions.
    # Note: resolution_summary_tool is not defined here, so it's commented out.
    # You would define it as a local tool if needed.
    root_agent = LlmAgent(
        model=llm,
        name="email_summary_agent",
        instruction="""

        You are an Email Summarizer agent.
""",
        tools=mcp_tools if mcp_tools else []
    )
    print("🤖 Agent created successfully with remote tools.")

    # 5. Setup session and runner
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="cases_ai_app",
        user_id="user_1",
        session_id="session_1"
    )

    runner = Runner(
        agent=root_agent,
        app_name="cases_ai_app",
        session_service=session_service
    )

    # 6. Define a relevant task and run the agent.
    task = "Run the search_by_config with the CVCS config and tell me how many recent (7d) emails you find, and who sent the most emails. Highlight 1 interesting email."
    print(f"\n💬 Giving agent task: '{task}'")
    print("⏳ Agent is running...")

    try:
        await call_agent_async(runner, task)
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
