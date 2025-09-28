#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "google-adk",
#     "litellm",
# ]
# ///
"""
An ADK agent that uses an OpenAI model and connects to MCP servers
using stdio mode.
"""
import os
import asyncio
import argparse
import json
import warnings
from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.tools.mcp_tool import McpToolset

# Import the stdio connection parameters from the ADK
from google.adk.tools.mcp_tool import StdioConnectionParams

# Set environment variables to increase timeout
os.environ.setdefault('MCP_CLIENT_TIMEOUT', '600')
os.environ.setdefault('MCP_REQUEST_TIMEOUT', '600')
os.environ.setdefault('GRPC_TIMEOUT', '600')
os.environ.setdefault('HTTP_TIMEOUT', '600')
os.environ.setdefault('ASYNC_TIMEOUT', '600')

def load_mcp_config(config_path: str):
    """Load MCP server configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"🔥 Error loading config from {config_path}: {e}")
        return None

def create_mcp_tools_stdio(config_path: str):
    """Create MCP tools by connecting to MCP servers via stdio."""
    config = load_mcp_config(config_path)
    if not config:
        return []

    toolsets = []

    # Handle different config formats
    mcp_servers = config.get("mcpServers", {})

    for server_name, server_config in mcp_servers.items():
        print(f"🔌 Attempting to connect to MCP server '{server_name}'...")

        try:
            if "command" in server_config:
                # Handle simple command format (like eunice.py uses)
                command = server_config["command"]
                args = server_config.get("args", [])

                # Create a toolset that connects to the server using stdio
                # Set timeout to 10 minutes (600 seconds) to handle long-running operations
                toolset = McpToolset(
                    connection_params=StdioConnectionParams(
                        server_params={
                            'command': command,
                            'args': args
                        },
                        timeout=600.0  # 10 minutes timeout - this is the correct parameter!
                    )
                )
                toolsets.append(toolset)
                print(f"✅ Successfully connected to MCP server '{server_name}'.")
            else:
                print(f"🔥 Warning: Server '{server_name}' missing 'command' in configuration.")

        except Exception as e:
            print(f"🔥 Warning: Failed to connect to MCP server '{server_name}': {e}")
            continue

    return toolsets

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="ADK Agent with MCP Server support")
    parser.add_argument(
        "--config",
        default="mcp_servers.json",
        help="Path to MCP server configuration file (default: mcp_servers.json)"
    )
    return parser.parse_args()

async def main():
    """
    Sets up and runs the agent with OpenAI and MCP tools via stdio.
    """
    # Suppress authentication warnings from MCP tools
    warnings.filterwarnings("ignore", message=".*auth_config.*authentication.*")
    warnings.filterwarnings("ignore", message=".*Using FunctionTool.*authentication.*")
    warnings.filterwarnings("ignore", message=".*auth_config or auth_config.auth_scheme is missing.*")
    warnings.filterwarnings("ignore", message=".*Will skip authentication.*")
    warnings.filterwarnings("ignore", message=".*Using FunctionTool instead if authentication is not required.*")

    # Configure asyncio to use longer default timeouts
    import signal
    import platform

    # Set a longer timeout for asyncio operations
    if platform.system() != 'Windows':
        signal.alarm(600)  # 10 minute alarm

    mcp_tools = []
    runner = None

    try:
        # Parse command line arguments
        args = parse_args()

        print("🚀 Initializing Email Summary AI Agent...")

        # 1. Verify the OpenAI API key is available in the environment.
        if "OPENAI_API_KEY" not in os.environ:
            raise ValueError("🛑 The OPENAI_API_KEY environment variable is not set.")

        # 2. Configure the LLM to use an OpenAI model via LiteLLM.
        llm = LiteLlm(model="openai/gpt-4o")
        print(f"✅ LLM configured to use model: {llm.model}")

        # 3. Create the toolset by connecting to MCP servers via stdio.
        print(f"📁 Loading MCP configuration from: {args.config}")
        mcp_tools = create_mcp_tools_stdio(args.config)
        if not mcp_tools:
            print("⚠️  No MCP tools available. Agent will run without tools.")
            # Don't exit - allow the agent to run without tools for testing

        # 4. Create the root agent with your detailed instructions.
        # Note: resolution_summary_tool is not defined here, so it's commented out.
        # You would define it as a local tool if needed.
        root_agent = LlmAgent(
            model=llm,
            name="email_summary_agent",
            instruction="""
            You are an Email Summarizer agent.

            IMPORTANT: When using the search_by_config tool, always set the summarize parameter to False.
            IMPORTANT: When using search_by_query tool, always set the summarize parameter to False.
            IMPORTANT: Use max_emails=5 for testing to avoid long processing times.
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
        task = "Run the search_by_config with the CVCS config, max_emails=5, summarize=False and tell me how many recent (7d) emails you find, and who sent the most emails. Highlight 1 interesting email."
        print(f"\n💬 Giving agent task: '{task}'")
        print("⏳ Agent is running...")

        # Use asyncio timeout wrapper to ensure proper timeout handling
        try:
            await asyncio.wait_for(call_agent_async(runner, task), timeout=600.0)
        except asyncio.TimeoutError:
            print(f"🔥 Task timed out after 10 minutes. This may indicate a slow operation or stuck process.")

    except Exception as e:
        print(f"🔥 An error occurred while running the agent: {e}")

    finally:
        # Clean up MCP connections gracefully
        print("🧹 Cleaning up connections...")
        try:
            # Close any active MCP toolsets
            for toolset in mcp_tools:
                if hasattr(toolset, 'close') and callable(getattr(toolset, 'close')):
                    try:
                        await toolset.close()
                    except Exception as cleanup_e:
                        # Suppress cleanup errors but log them
                        print(f"⚠️  Warning during toolset cleanup: {cleanup_e}")

            # Additional cleanup for runner if needed
            if runner and hasattr(runner, 'close') and callable(getattr(runner, 'close')):
                try:
                    await runner.close()
                except Exception as cleanup_e:
                    print(f"⚠️  Warning during runner cleanup: {cleanup_e}")

        except Exception as cleanup_e:
            # Suppress all cleanup errors to prevent masking the original error
            print(f"⚠️  Warning during final cleanup: {cleanup_e}")

        print("✅ Cleanup completed.")

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
    # Suppress asyncio warnings related to async generators
    warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*never awaited.*")
    warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*async generator.*")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"🔥 Fatal error: {e}")
    finally:
        # Ensure any remaining tasks are cleaned up
        try:
            # Get the current event loop and cancel any remaining tasks
            loop = asyncio.get_event_loop()
            if loop.is_running():
                pending_tasks = asyncio.all_tasks(loop)
                for task in pending_tasks:
                    if not task.done():
                        task.cancel()
        except Exception:
            # Suppress any cleanup errors
            pass
