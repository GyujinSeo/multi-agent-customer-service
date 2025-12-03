#!/usr/bin/env python3
"""
MCP Server Implementation using Official MCP Python SDK
Provides customer service tools via Model Context Protocol.
"""

import sqlite3
import json
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("Customer Service MCP Server")

DB_PATH = "support.db"

def get_db_connection():
    """Get SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@mcp.tool()
def get_customer(customer_id: int) -> str:
    """
    Retrieve customer information by customer ID.
    
    Args:
        customer_id: The unique customer ID
        
    Returns:
        JSON string with customer data or error message
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM customers WHERE id = ?', (customer_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        customer = dict(row)
        return json.dumps(customer, indent=2)
    else:
        return json.dumps({"error": f"Customer with ID {customer_id} not found"})

@mcp.tool()
def list_customers(status: str = None, limit: int = 10) -> str:
    """
    List customers with optional filtering by status.
    
    Args:
        status: Filter by customer status ('active' or 'disabled'). Optional.
        limit: Maximum number of customers to return. Default is 10.
        
    Returns:
        JSON string with list of customers
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if status:
        cursor.execute(
            'SELECT * FROM customers WHERE status = ? LIMIT ?',
            (status, limit)
        )
    else:
        cursor.execute('SELECT * FROM customers LIMIT ?', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    customers = [dict(row) for row in rows]
    return json.dumps(customers, indent=2)

@mcp.tool()
def update_customer(customer_id: int, name: str = None, email: str = None, 
                   phone: str = None, status: str = None) -> str:
    """
    Update customer information.
    
    Args:
        customer_id: The unique customer ID
        name: New name (optional)
        email: New email (optional)
        phone: New phone (optional)
        status: New status - 'active' or 'disabled' (optional)
        
    Returns:
        Success or error message
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build update query dynamically
    fields = []
    values = []
    
    if name:
        fields.append("name = ?")
        values.append(name)
    if email:
        fields.append("email = ?")
        values.append(email)
    if phone:
        fields.append("phone = ?")
        values.append(phone)
    if status:
        fields.append("status = ?")
        values.append(status)
    
    if not fields:
        conn.close()
        return json.dumps({"error": "No fields to update"})
    
    fields.append("updated_at = ?")
    values.append(datetime.now().isoformat())
    values.append(customer_id)
    
    query = f"UPDATE customers SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()
    
    updated = cursor.rowcount > 0
    conn.close()
    
    if updated:
        return json.dumps({"success": True, "message": f"Customer {customer_id} updated successfully"})
    else:
        return json.dumps({"error": f"Customer {customer_id} not found"})

@mcp.tool()
def create_ticket(customer_id: int, issue: str, priority: str = "medium") -> str:
    """
    Create a new support ticket for a customer.
    
    Args:
        customer_id: The customer ID
        issue: Description of the issue
        priority: Ticket priority - 'low', 'medium', or 'high'. Default is 'medium'.
        
    Returns:
        Success message with ticket ID or error
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO tickets (customer_id, issue, priority, status)
        VALUES (?, ?, ?, 'open')
    ''', (customer_id, issue, priority))
    
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return json.dumps({
        "success": True,
        "ticket_id": ticket_id,
        "message": f"Ticket created successfully with ID: {ticket_id}"
    })

@mcp.tool()
def get_customer_history(customer_id: int) -> str:
    """
    Get all tickets for a specific customer.
    
    Args:
        customer_id: The unique customer ID
        
    Returns:
        JSON string with list of tickets
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM tickets 
        WHERE customer_id = ? 
        ORDER BY created_at DESC
    ''', (customer_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    tickets = [dict(row) for row in rows]
    return json.dumps(tickets, indent=2)

if __name__ == "__main__":
    print("=" * 80)
    print("  MCP SERVER - Customer Service")
    print("  Using Official FastMCP (Auto-managed transport)")
    print("=" * 80)
    # [FIX] Use mcp.run() to automatically handle /sse and /messages routes correctly
    mcp.run(transport="sse")