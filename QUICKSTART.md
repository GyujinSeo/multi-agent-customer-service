# Quick Start Guide

## 🚀 5-Minute Setup

### Step 1: Clone and Setup

```bash
# Navigate to your project directory
cd multi-agent-customer-service

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Anthropic API key
# You can get one from: https://console.anthropic.com/
nano .env  # or use any text editor

# Add this line:
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
```

### Step 3: Create Database

```bash
python database_setup.py
```

**Interactive Setup:**
1. Shows database schema
2. Asks: "Would you like to insert sample data? (y/n)"
   - Type `y` to create 15 customers and 25 tickets
3. Asks: "Would you like to run sample queries? (y/n)"
   - Type `y` to see example queries and data

**What gets created:**
- `support.db` - SQLite database file
- 15 test customers (active and disabled)
- 25 sample support tickets (all priorities)

### Step 4: Start Services

**Option A: All in one terminal (recommended for testing)**

```bash
python run_system.py
```

Wait for all 4 services to start (takes ~15 seconds):
- ✓ MCP Server (port 8000)
- ✓ Customer Data Agent (port 5001)
- ✓ Support Agent (port 5002)
- ✓ Router Agent (port 5003)

**Option B: Individual terminals (recommended for development)**

```bash
# Terminal 1: MCP Server
python mcp_server.py

# Terminal 2: Customer Data Agent
python a2a_agents.py data

# Terminal 3: Support Agent
python a2a_agents.py support

# Terminal 4: Router Agent
python a2a_agents.py router
```

### Step 5: Verify Services

Open a new terminal:

```bash
# Check A2A Agent Cards
curl http://localhost:5001/.well-known/agent.json
curl http://localhost:5002/.well-known/agent.json
curl http://localhost:5003/.well-known/agent.json

# Test MCP Server with official tool
mcp dev mcp_server.py
```

### Step 6: Run Tests

```bash
python test_system.py
```

## 📝 Quick Test Examples

### Test 1: Simple Customer Lookup

```bash
curl -X POST http://localhost:5003 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-1",
    "method": "tasks/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{
          "type": "text",
          "text": "Get customer information for ID 5"
        }]
      }
    }
  }'
```

### Test 2: Support Request

```bash
curl -X POST http://localhost:5003 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-2",
    "method": "tasks/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{
          "type": "text",
          "text": "Customer ID 3 needs help upgrading account"
        }]
      }
    }
  }'
```

### Test 3: Urgent Escalation

```bash
curl -X POST http://localhost:5003 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-3",
    "method": "tasks/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{
          "type": "text",
          "text": "Customer ID 7 charged twice, need refund immediately!"
        }]
      }
    }
  }'
```

## 🔍 Verifying SDK Compliance

### MCP SDK Verification

```bash
# Install MCP Inspector (if not already installed)
npm install -g @modelcontextprotocol/inspector

# Test with MCP Inspector
mcp dev mcp_server.py

# This will:
# 1. Start the MCP server
# 2. List all available tools
# 3. Allow interactive testing
```

Expected output:
```
Available tools:
  - get_customer
  - list_customers
  - update_customer
  - create_ticket
  - get_customer_history
```

### A2A SDK Verification

```bash
# Check Agent Card format (must follow A2A spec)
curl http://localhost:5001/.well-known/agent.json | jq .

# Expected fields:
# - name
# - description
# - version
# - capabilities
# - skills[]
# - url
```

## 🐛 Troubleshooting

### Issue: Port already in use

```bash
# Find process using port
lsof -i :8000  # Replace with your port
# Or on Windows:
netstat -ano | findstr :8000

# Kill the process
kill -9 <PID>
```

### Issue: ModuleNotFoundError

```bash
# Ensure you're in the virtual environment
source venv/bin/activate  # or venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### Issue: Database locked

```bash
# Remove and recreate database
rm customer_service.db
python database_setup.py
```

### Issue: API key not set

```bash
# Set in current terminal
export ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx

# Or add to .env file
echo "ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx" > .env
```

## 📚 Next Steps

1. **Read the full README.md** for detailed documentation
2. **Explore the code** to understand SDK integration
3. **Modify test scenarios** in `test_system.py`
4. **Add new MCP tools** in `mcp_server.py`
5. **Extend agent capabilities** in `a2a_agents.py`

## ✅ Assignment Checklist

- [ ] All services start without errors
- [ ] MCP Inspector can list tools
- [ ] Agent Cards are accessible
- [ ] Test suite passes all scenarios
- [ ] README documents SDK usage
- [ ] Code follows SDK patterns

## 🎓 Key SDK Features Used

**MCP Python SDK (FastMCP):**
- `@mcp.tool()` decorator for automatic tool registration
- SSE transport for real-time communication
- Automatic JSON Schema generation

**Google A2A SDK:**
- `A2AStarletteApplication` for agent servers
- `AgentExecutor` pattern for agent logic
- `AgentCard` for capability declaration
- `InMemoryTaskStore` for task management

**LangGraph:**
- `StateGraph` for agent workflows
- `MessagesState` for conversation state
- Integration with A2A via `AgentExecutor`

## 📞 Support

If you encounter issues:
1. Check the error messages carefully
2. Verify all dependencies are installed
3. Ensure API keys are set correctly
4. Review the logs for each service

Happy coding! 🚀
