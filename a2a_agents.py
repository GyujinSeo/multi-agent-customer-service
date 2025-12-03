import sys
import uvicorn
import httpx
import os
import asyncio
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

# LangChain & LangGraph Imports (The "Brain")
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

# Official MCP SDK Imports (Connects to your mcp_server.py)
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client

from fastapi import FastAPI, Request

# ==========================================
# 1. Configuration & Initialization
# ==========================================

# Determine which agent to run based on command line argument (data, support, router)
AGENT_TYPE = sys.argv[1] if len(sys.argv) > 1 else "data"

# Port configuration
PORTS = {
    "data": 5001,
    "support": 5002,
    "router": 5003
}

# A2A Communication URLs
URLS = {
    "data": "http://localhost:5001",
    "support": "http://localhost:5002",
    "router": "http://localhost:5003"
}

# MCP Server URL (Must match where mcp_server.py is running)
MCP_SERVER_SSE_URL = "http://localhost:8000/sse"

# Check for API Key
if not os.getenv("ANTHROPIC_API_KEY"):
    print("⚠️ WARNING: ANTHROPIC_API_KEY not found. Agent logic will fail.")

# Initialize LLM (The "Brain")
# [FIXED FINAL] Switched to Claude 3 Haiku. This model is available to ALL API keys.
# It is fast, cheap, and capable enough for this assignment.
llm = ChatAnthropic(model="claude-3-haiku-20240307", temperature=0)

# ==========================================
# 2. System Prompts (Moved to Global Dict)
# ==========================================
# Managed here to avoid function parameter conflicts and injected at runtime.
SYSTEM_PROMPTS = {
    "router": """You are the Router Agent (Orchestrator).
Your goal is to coordinate customer service requests.

INSTRUCTIONS:
1. Analyze the user's request.
2. Identify which specialist agent is needed:
    - 'data' agent: For customer lookups, email updates, or checking status.
    - 'support' agent: For ticket creation, history checks, or technical problems.
3. Use the 'delegate_to_specialist' tool to assign the task.
4. If the request involves both (e.g., "Update email and create ticket"), call them sequentially.
5. Synthesize the final answer based on the reports from the specialists.

Do NOT attempt to access the database directly. You must delegate.""",

    "data": """You are the Customer Data Specialist.
You access the database via the MCP Server.

INSTRUCTIONS:
- Use 'get_customer' to find individual user details.
- Use 'list_customers' to find groups of users.
- Use 'update_customer_email' to modify records.
- If a tool fails, report the error clearly.
- Provide concise, data-driven answers.""",

    "support": """You are the Support Agent.
You manage tickets via the MCP Server.

INSTRUCTIONS:
- Use 'create_ticket' for new issues. 
    * CRITICAL: Analyze the user's tone. If angry or urgent -> priority='high'.
- Use 'get_customer_history' to see past issues.
- Always provide the Ticket ID when a new ticket is created."""
}

# ==========================================
# 3. MCP Client Helper
# ==========================================

async def call_mcp_tool(tool_name: str, arguments: dict) -> str:
    """
    Connects to the running MCP Server via SSE and executes a tool.
    This ensures we are using the official MCP protocol for data access.
    """
    print(f"    [MCP Client] Connecting to {MCP_SERVER_SSE_URL} to call '{tool_name}'...")
    try:
        # Connect to MCP Server using SSE Transport
        async with sse_client(MCP_SERVER_SSE_URL) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                
                # Call the tool on the MCP server
                result = await session.call_tool(tool_name, arguments)
                
                # Parse result (MCP returns a list of content objects)
                if result.content:
                    text_content = result.content[0].text
                    # Check if the tool returned an error JSON string
                    if "error" in text_content.lower() and "{" in text_content:
                        return f"Tool Error: {text_content}"
                    return text_content
                
                return "No output returned from MCP tool."
                
    except Exception as e:
        error_msg = f"Failed to communicate with MCP Server: {str(e)}. Is mcp_server.py running on port 8000?"
        print(f"    [MCP Client Error] {error_msg}")
        return error_msg


# ==========================================
# 4. Tool Definitions (Agent Capabilities)
# ==========================================

# --- Tools for Customer Data Agent (Wraps MCP calls) ---

@tool
async def get_customer(customer_id: int):
    """
    Retrieve customer details (name, email, status) by ID via MCP.
    """
    return await call_mcp_tool("get_customer", {"customer_id": customer_id})

@tool
async def list_customers(status: str = "active"):
    """
    List customers filtered by status ('active' or 'disabled') via MCP.
    """
    return await call_mcp_tool("list_customers", {"status": status, "limit": 5})

@tool
async def update_customer_email(customer_id: int, new_email: str):
    """
    Update a customer's email address via MCP.
    """
    # Note: Using 'update_customer' tool on the server side
    return await call_mcp_tool("update_customer", {"customer_id": customer_id, "email": new_email})


# --- Tools for Support Agent (Wraps MCP calls) ---

@tool
async def create_ticket(customer_id: int, issue: str, priority: str = "medium"):
    """
    Create a support ticket via MCP.
    Priority must be one of: 'low', 'medium', 'high'.
    Use 'high' if the customer is angry or the issue is critical.
    """
    return await call_mcp_tool("create_ticket", {"customer_id": customer_id, "issue": issue, "priority": priority})

@tool
async def get_customer_history(customer_id: int):
    """
    Get support ticket history for a customer via MCP.
    """
    return await call_mcp_tool("get_customer_history", {"customer_id": customer_id})


# --- Tools for Router Agent (A2A Communication) ---

@tool
async def delegate_to_specialist(agent_name: str, task_description: str):
    """
    Delegate a task to a specialist agent using HTTP (A2A Protocol).
    - Use 'data' agent for: getting customer info, listing users, updating details.
    - Use 'support' agent for: creating tickets, checking history, solving technical issues.
    """
    url = URLS.get(agent_name)
    if not url:
        return f"Error: Specialist agent '{agent_name}' is not configured."
    
    print(f"    [Router -> {agent_name}] Delegating task: {task_description}")
    
    try:
        async with httpx.AsyncClient() as client:
            # Call the /execute endpoint of the other agent
            response = await client.post(
                f"{url}/execute", 
                json={"query": task_description}, 
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json().get("result")
                print(f"    [Router <- {agent_name}] Task completed.")
                return f"Result from {agent_name}: {result}"
            else:
                return f"Error from {agent_name}: {response.text}"
                
    except Exception as e:
        return f"Failed to contact {agent_name} agent: {str(e)}"


# ==========================================
# 5. Agent Factory (LangGraph)
# ==========================================

def get_agent_tools() -> list:
    """Helper function to get list of tools for current agent type."""
    if AGENT_TYPE == "router":
        return [delegate_to_specialist]
    elif AGENT_TYPE == "data":
        return [get_customer, list_customers, update_customer_email]
    elif AGENT_TYPE == "support":
        return [create_ticket, get_customer_history]
    else:
        raise ValueError(f"Invalid Agent Type: {AGENT_TYPE}")

def build_agent_graph():
    """
    Builds the ReAct agent graph with the appropriate tools based on AGENT_TYPE.
    NOTE: System prompt is injected at runtime (in execute_task) to avoid version issues.
    """
    tools = get_agent_tools()
    # Create the ReAct agent (LLM + Tools + Loop)
    return create_react_agent(llm, tools=tools)


# ==========================================
# 6. FastAPI Application
# ==========================================

app = FastAPI(title=f"{AGENT_TYPE.capitalize()} Agent")
agent_runnable = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: Initialize the AI agent on startup."""
    global agent_runnable
    # [FIX] Print model name in logs (for debugging)
    print(f"[{AGENT_TYPE.upper()}] Initializing Agent (Model: {llm.model})...")
    agent_runnable = build_agent_graph()
    print(f"[{AGENT_TYPE.upper()}] Agent Ready. Listening on port {PORTS[AGENT_TYPE]}")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/a2a/{assistant_id}")
async def get_agent_card():    
    """
    A2A Protocol Discovery Endpoint.
    Returns the agent's capabilities (tools) so other agents can understand it.
    """

    tools_list = [t.name for t in get_agent_tools()]
    
    return {
        "name": f"{AGENT_TYPE.capitalize()} Agent",
        "description": f"AI Specialist for {AGENT_TYPE} operations",
        "protocol": "A2A-JSON-RPC",
        "capabilities": tools_list
    }

@app.post("/execute")
async def execute_task(request: Request):
    """
    Main execution endpoint.
    Receives a task, processes it with the LLM (ReAct loop), and returns the result.
    """
    data = await request.json()
    user_query = data.get("query")
    
    if not agent_runnable:
        return {"success": False, "error": "Agent not initialized"}

    print(f"\n[{AGENT_TYPE.upper()}] Received Task: {user_query}")
    
    # [FIX] Inject System Prompt here as a message
    system_msg = SYSTEM_PROMPTS.get(AGENT_TYPE, "You are a helpful assistant.")
    
    try:
        # Invoke the LangGraph agent
        # The LLM will loop: Think -> Call Tool (MCP/A2A) -> Observe -> Think -> Answer
        inputs = {
            "messages": [
                SystemMessage(content=system_msg),  # Inject Persona
                HumanMessage(content=user_query)    # User Request
            ]
        }
        
        result = await agent_runnable.ainvoke(inputs)
        
        # Extract the final response text
        final_response = result["messages"][-1].content
        print(f"[{AGENT_TYPE.upper()}] Final Response: {final_response[:60]}...")
        
        return {
            "success": True,
            "result": final_response,
            "agent": AGENT_TYPE
        }
        
    except Exception as e:
        error_msg = f"Agent execution failed: {str(e)}"
        print(f"[{AGENT_TYPE.upper()}] Error: {error_msg}")
        # Print full traceback for debugging
        import traceback
        traceback.print_exc()
        return {"success": False, "error": error_msg}


if __name__ == "__main__":
    # Run the server
    port = PORTS.get(AGENT_TYPE, 5001)
    uvicorn.run(app, host="0.0.0.0", port=port)