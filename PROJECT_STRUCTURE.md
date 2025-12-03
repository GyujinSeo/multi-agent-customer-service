# Project Structure

## 📁 Complete File Listing

```
multi-agent-customer-service/
│
├── 📄 database_setup.py          # Database initialization script
├── 📄 mcp_server.py               # MCP Server (Official MCP SDK)
├── 📄 a2a_agents.py               # A2A Agents (Google SDK + LangGraph)
├── 📄 run_system.py               # Main launcher for all services
├── 📄 test_system.py              # E2E test suite
├── 📄 demo_queries.py             # Interactive demo script (optional)
│
├── 📄 requirements.txt            # Python dependencies
├── 📄 .env.example                # Environment variables template
├── 📄 README.md                   # Main documentation
├── 📄 QUICKSTART.md               # Quick setup guide
├── 📄 PROJECT_STRUCTURE.md        # This file
│
├── 🗄️ support.db                  # SQLite database (auto-created)
└── 📁 venv/                       # Virtual environment (auto-created)
```

## 📝 File Descriptions

### Core Implementation Files

#### 1. `database_setup.py` (Database Setup)
**Purpose**: Creates SQLite database with schema and test data  
**SDK**: None (uses built-in sqlite3)  
**Provided by**: Professor (Assignment 5)  
**Key Features**:
- Object-oriented design with DatabaseSetup class
- Creates `customers` table (15 test customers)
- Creates `tickets` table (25 sample tickets)
- Indexes for performance (email, customer_id, status)
- Triggers for automatic timestamp updates
- Foreign key constraints with CASCADE delete
- Interactive CLI for data insertion
- 10 sample queries demonstrating database functionality

**Schema Details**:
```sql
customers:
  - id (PRIMARY KEY, AUTOINCREMENT)
  - name, email, phone
  - status ('active'|'disabled') with CHECK constraint
  - created_at, updated_at (automatic timestamps)
  
tickets:
  - id (PRIMARY KEY, AUTOINCREMENT)
  - customer_id (FK → customers with CASCADE)
  - issue, status, priority (with CHECK constraints)
  - created_at (automatic timestamp)
```

**Sample Data**:
- 15 customers: Mix of active/disabled, realistic emails
- 25 tickets: 
  - 5 high priority (login issues, security, payments)
  - 8 medium priority (bugs, performance)
  - 12 low priority (feature requests, UI tweaks)
  - Status: open, in_progress, resolved

**Interactive Features**:
- Prompts for sample data insertion
- Option to run 10 demonstration queries
- Displays schema information
- Shows indexes and foreign keys

**Usage**:
```bash
python database_setup.py
# Answer prompts:
# Would you like to insert sample data? (y/n): y
# Would you like to run sample queries? (y/n): y
```

---

#### 2. `mcp_server.py` (MCP Server)
**Purpose**: Provides customer service tools via MCP protocol  
**SDK**: **Official MCP Python SDK (FastMCP)**  
**Port**: 8000  
**Transport**: SSE (Server-Sent Events)

**Key Components**:
```python
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

mcp = FastMCP("Customer Service MCP Server")

@mcp.tool()
def get_customer(customer_id: int) -> str:
    # Tool implementation
```

**Available Tools**:
1. `get_customer(customer_id)` - Retrieve customer info
2. `list_customers(status, limit)` - List customers
3. `update_customer(customer_id, ...)` - Update customer data
4. `create_ticket(customer_id, issue, priority)` - Create support ticket
5. `get_customer_history(customer_id)` - Get ticket history

**Testing**:
```bash
# Start server
python mcp_server.py

# Test with MCP Inspector
mcp dev mcp_server.py
```

**Endpoints**:
- SSE: `http://localhost:8000/sse`

---

#### 3. `a2a_agents.py` (A2A Agents)
**Purpose**: Three intelligent agents with A2A protocol  
**SDK**: **Google A2A SDK + LangGraph**  
**Ports**: 5001 (Data), 5002 (Support), 5003 (Router)

**Architecture**:
```python
# LangGraph Agent
from langgraph.graph import StateGraph, MessagesState

def create_customer_data_agent():
    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", agent_node)
    return workflow.compile()

# A2A Integration
from a2a.server.apps import A2AStarletteApplication
from a2a.server.agent_execution import AgentExecutor

class CustomerDataAgentExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        # Run LangGraph agent
        result = await self.agent.ainvoke(...)
```

**Three Agents**:

**1. CustomerDataAgent (Port 5001)**
- Handles customer data operations
- Calls MCP tools: get_customer, list_customers, update_customer, get_customer_history
- Skills: retrieve_customer_data, update_customer_data, customer_history

**2. SupportAgent (Port 5002)**
- Handles support requests
- Calls MCP tools: create_ticket
- Detects urgency and escalates
- Skills: create_support_ticket, handle_support_query, escalate_issues

**3. RouterAgent (Port 5003)**
- Orchestrator for routing requests
- Analyzes intent and routes to specialists
- Coordinates multi-agent workflows
- Skills: route_customer_query, coordinate_multi_agent

**Usage**:
```bash
# Start individual agents
python a2a_agents.py data     # Customer Data Agent
python a2a_agents.py support  # Support Agent
python a2a_agents.py router   # Router Agent
```

**A2A Endpoints**:
Each agent exposes:
- Agent Card: `/.well-known/agent.json`
- Task endpoint: `/` (POST with JSON-RPC)
- Task status: `/tasks/{task_id}` (GET)

---

#### 4. `run_system.py` (System Launcher)
**Purpose**: Start all services in correct order  
**Features**:
- Starts MCP server + 3 A2A agents
- Health checks for each service
- Graceful shutdown on Ctrl+C
- Process management

**Usage**:
```bash
python run_system.py
```

**Startup Sequence**:
1. Check database exists (create if missing)
2. Start MCP Server (port 8000)
3. Start Customer Data Agent (port 5001)
4. Start Support Agent (port 5002)
5. Start Router Agent (port 5003)
6. Health check all services
7. Display status and URLs

---

#### 5. `test_system.py` (Test Suite)
**Purpose**: End-to-end testing of all scenarios  
**Framework**: asyncio + httpx  
**Tests**:

**Test 1: A2A Agent Card Discovery**
- Verify all agents expose Agent Cards
- Check card format compliance

**Test 2: MCP Server Availability**
- Verify MCP server is running
- Check SSE endpoint

**Scenario 1: Simple Query**
- Single agent, direct MCP call
- "Get customer information for ID 5"

**Scenario 2: Coordinated Query**
- Multi-agent coordination
- "I'm customer ID 3 and need help upgrading"

**Scenario 3: Multi-Step Coordination**
- Sequential/parallel tasks
- "Get ticket history for customer ID 1"

**Scenario 4: Escalation**
- Priority detection and routing
- "Customer ID 7 charged twice, refund immediately!"

**Scenario 5: Data Aggregation**
- List operations with filtering
- "List all active customers"

**Test 6: Direct Agent Call**
- Bypass router, call agent directly

**Usage**:
```bash
python test_system.py
```

---

#### 6. `demo_queries.py` (Interactive Demo)
**Purpose**: Interactive CLI for testing queries  
**Features**:
- Pre-built demo scenarios
- Interactive query input
- Formatted output display

**Usage**:
```bash
python demo_queries.py
```

---

### Configuration Files

#### 7. `requirements.txt` (Dependencies)
**Python Packages**:
```
# Core SDKs
mcp==1.22.0                    # Official MCP Python SDK
a2a-sdk>=0.1.0                 # Google A2A SDK
langgraph>=0.2.40              # LangGraph for workflows
langchain>=0.3.0               # LangChain core
langchain-anthropic>=0.3.0     # Anthropic integration

# Web servers
uvicorn>=0.30.0                # ASGI server
starlette>=0.37.0              # Web framework

# HTTP client
httpx>=0.27.0                  # Async HTTP
aiohttp>=3.10.0                # Alternative async HTTP

# Database
aiosqlite>=0.20.0              # Async SQLite

# Utilities
python-dotenv>=1.0.0           # Environment variables
pydantic>=2.0.0                # Data validation
typing-extensions>=4.12.0      # Type hints

# Development
pytest>=8.0.0                  # Testing framework
pytest-asyncio>=0.23.0         # Async tests
```

---

#### 8. `.env.example` (Environment Template)
**Environment Variables**:
```bash
ANTHROPIC_API_KEY=your_key_here
MCP_SERVER_PORT=8000
DATA_AGENT_PORT=5001
SUPPORT_AGENT_PORT=5002
ROUTER_AGENT_PORT=5003
LOG_LEVEL=INFO
```

---

### Documentation Files

#### 9. `README.md` (Main Documentation)
**Sections**:
- Overview and architecture
- SDK compliance details
- Setup instructions
- Testing guides
- API documentation
- Troubleshooting
- Assignment requirements checklist

#### 10. `QUICKSTART.md` (Quick Setup)
**5-Minute Guide**:
- Step-by-step setup
- Quick test examples
- Verification commands
- Troubleshooting tips

#### 11. `PROJECT_STRUCTURE.md` (This File)
**Complete Overview**:
- File descriptions
- Code architecture
- SDK usage patterns
- Development workflow

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User / Test Client                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   RouterAgent        │ ← LangGraph StateGraph
              │   (Port 5003)        │ ← A2A AgentExecutor
              │   Google A2A SDK     │ ← Agent Card
              └──────┬───────┬───────┘
                     │       │
         ┌───────────┘       └───────────┐
         │                               │
         ▼                               ▼
┌────────────────────┐         ┌────────────────────┐
│ CustomerDataAgent  │         │  SupportAgent      │
│ (Port 5001)        │         │  (Port 5002)       │
│ Google A2A SDK     │         │  Google A2A SDK    │
│ LangGraph          │         │  LangGraph         │
└────────┬───────────┘         └────────┬───────────┘
         │                               │
         │          MCP Protocol         │
         │      (Official Python SDK)    │
         └───────────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │    MCP Server         │
              │    (Port 8000)        │
              │    FastMCP            │
              │    SSE Transport      │
              └──────────┬────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   SQLite Database     │
              │   customer_service.db │
              └───────────────────────┘
```

---

## 🔄 Data Flow Examples

### Example 1: Simple Customer Lookup

```
1. User → RouterAgent: "Get customer info for ID 5"
2. RouterAgent analyzes intent → routes to CustomerDataAgent
3. CustomerDataAgent → MCP Server: call tool "get_customer"
4. MCP Server → SQLite: SELECT * FROM customers WHERE id=5
5. SQLite → MCP Server: customer data
6. MCP Server → CustomerDataAgent: JSON response
7. CustomerDataAgent → RouterAgent: formatted result
8. RouterAgent → User: final response
```

### Example 2: Support with Context

```
1. User → RouterAgent: "Customer ID 3 needs help upgrading"
2. RouterAgent detects: support request + customer ID
3. RouterAgent → CustomerDataAgent: "Get customer 3 info"
4. CustomerDataAgent → MCP: get_customer(3)
5. MCP → RouterAgent: customer context
6. RouterAgent → SupportAgent: "Handle upgrade with context"
7. SupportAgent → MCP: create_ticket(3, "upgrade", "medium")
8. MCP → SupportAgent: ticket created
9. SupportAgent → RouterAgent: ticket confirmation
10. RouterAgent → User: coordinated response
```

---

## 🛠️ Development Workflow

### Adding a New MCP Tool

1. Edit `mcp_server.py`
2. Add function with `@mcp.tool()` decorator
3. Implement tool logic with database access
4. Restart MCP server
5. Test with: `mcp dev mcp_server.py`

### Adding Agent Capability

1. Edit `a2a_agents.py`
2. Add new skill to AgentCard
3. Implement logic in agent_node function
4. Update LangGraph workflow if needed
5. Restart agent
6. Test A2A endpoint

### Adding Test Scenario

1. Edit `test_system.py`
2. Create new async test function
3. Define expected A2A flow
4. Send task and verify response
5. Add to main() test sequence

---

## 📊 SDK Compliance Matrix

| Component | SDK Used | Compliance Points |
|-----------|----------|-------------------|
| MCP Server | Official MCP Python SDK (FastMCP) | ✅ @mcp.tool() decorators<br>✅ SSE transport<br>✅ MCP Inspector compatible |
| A2A Agents | Google A2A SDK | ✅ A2AStarletteApplication<br>✅ AgentExecutor pattern<br>✅ Agent Cards |
| Agent Logic | LangGraph | ✅ StateGraph workflows<br>✅ MessagesState<br>✅ Async execution |
| Database | sqlite3 (built-in) | ✅ Proper schema<br>✅ Foreign keys<br>✅ Test data |
| Testing | httpx + asyncio | ✅ Async tests<br>✅ JSON-RPC format<br>✅ Full scenarios |

---

## 🎓 Learning Path

**For Understanding MCP**:
1. Read `mcp_server.py` - See FastMCP in action
2. Run `mcp dev mcp_server.py` - Interactive testing
3. Study tool decorator pattern

**For Understanding A2A**:
1. Review Agent Card format in `a2a_agents.py`
2. Study AgentExecutor pattern
3. Test with curl commands
4. Examine task lifecycle

**For Understanding Multi-Agent**:
1. Trace a query through `test_system.py`
2. Study RouterAgent coordination logic
3. See how agents communicate
4. Understand state management

---

## 📦 Deployment Checklist

- [ ] All dependencies in requirements.txt
- [ ] Environment variables documented
- [ ] Database initialization automated
- [ ] Services start in correct order
- [ ] Health checks implemented
- [ ] Error handling comprehensive
- [ ] Logging properly configured
- [ ] Tests cover all scenarios
- [ ] Documentation complete
- [ ] SDK compliance verified

---

**Last Updated**: 2025  
**Assignment**: Multi-Agent Customer Service System  
**SDKs**: MCP Python SDK + Google A2A SDK + LangGraph
