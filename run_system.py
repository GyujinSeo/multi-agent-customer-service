#!/usr/bin/env python3
"""
Main System Launcher for Multi-Agent Customer Service System
Starts all components: MCP Server + A2A Agents (using official SDKs)
"""

import subprocess
import sys
import time
import os
import signal
import httpx

processes = []

def cleanup(signum=None, frame=None):
    """Cleanup all processes on exit."""
    print("\n\nShutting down all services...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=3)
        except:
            try:
                p.kill()
            except:
                pass
    print("All services stopped.")
    sys.exit(0)

def check_service(url, name, process=None, max_retries=15):
    """Check if a service is ready, failing fast if the process dies."""
    import time
    
    print(f"Checking {name}...", end="", flush=True)
    
    for i in range(max_retries):

        if process and process.poll() is not None:
            print(f"\n\n❌ {name} Failed to start! (Process exited with code {process.returncode})")

            stdout, stderr = process.communicate()
            if stdout: print(f"--- STDOUT ---\n{stdout}")
            if stderr: print(f"--- STDERR ---\n{stderr}")
            return False


        try:
            response = httpx.get(url, timeout=2.0, follow_redirects=True)
            if response.status_code in [200, 404, 405]:
                print(f" ✓ Ready!")
                return True
        except:
            pass
        
        print(".", end="", flush=True)
        time.sleep(1.5)
    
    print(f"\n❌ {name} timed out (Not responding after {max_retries*1.5}s)")
    return False

def start_process(command, name):
    """Start a process and return the Popen object."""
    print(f"Starting {name}...", end=" ")
    try:
        # bufsize=0 (Unbuffered) to see errors immediately
        p = subprocess.Popen(
            command,
            stdout=sys.stdout,  # Print directly to console so user can see errors
            stderr=sys.stderr,
            bufsize=0,
            universal_newlines=True
        )
        processes.append(p)
        print(f"(PID: {p.pid})")
        return p
    except Exception as e:
        print(f"\nFailed to launch {name}: {e}")
        return None

def main():
    global processes
    
    # Register cleanup handler
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    print("="*80)
    print("  MULTI-AGENT SYSTEM LAUNCHER (SMART MODE)")
    print("="*80)
    
    # Check environment
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n⚠️  CRITICAL WARNING: ANTHROPIC_API_KEY is missing!")
        print("   Agents will crash immediately without it.")
        print("   Run: export ANTHROPIC_API_KEY=your_key_here\n")
        time.sleep(2)
    
    # Check database
    if not os.path.exists('support.db'):
        print("Creating database...")
        subprocess.run([sys.executable, 'database_setup.py'], check=True)
    
    # 1. Start MCP Server
    mcp_process = start_process([sys.executable, 'mcp_server.py'], "MCP Server")
    if not check_service("http://localhost:8000/health", "MCP Server", mcp_process):
        cleanup()
    
    # 2. Start Customer Data Agent
    data_process = start_process([sys.executable, 'a2a_agents.py', 'data'], "Data Agent")
    if not check_service("http://localhost:5001/a2a/data", "Data Agent", data_process):
        cleanup()

    # 3. Start Support Agent
    support_process = start_process([sys.executable, 'a2a_agents.py', 'support'], "Support Agent")
    if not check_service("http://localhost:5002/a2a/support", "Support Agent", support_process):
        cleanup()

    # 4. Start Router Agent
    router_process = start_process([sys.executable, 'a2a_agents.py', 'router'], "Router Agent")
    if not check_service("http://localhost:5003/a2a/router", "Router Agent", router_process):
        cleanup()
    
    print("\n" + "="*80)
    print("  ✅ ALL SYSTEMS GO!")
    print("="*80)
    print("  MCP Server:    http://localhost:8000")
    print("  Data Agent:    http://localhost:5001")
    print("  Support Agent: http://localhost:5002")
    print("  Router Agent:  http://localhost:5003")
    print("\nRun tests in a new terminal: python test_system.py")
    
    try:
        while True:
            time.sleep(1)
            # Monitor for sudden crashes
            for p in processes:
                if p.poll() is not None:
                    print(f"\n❌ A service process died unexpectedly! Shutting down...")
                    cleanup()
    except KeyboardInterrupt:
        cleanup()

if __name__ == '__main__':
    main()