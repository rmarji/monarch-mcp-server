#!/usr/bin/env python3
"""
Monarch Money MCP Server (Read-Only) - Updated for latest API
"""

import asyncio
import os
from typing import Any, Dict, Optional, List
import json

# Import the monarch money library
try:
    from monarchmoney import MonarchMoney, RequireMFAException
except ImportError:
    print("Error: monarchmoney package not found. Please install it with: uv add monarchmoney")
    exit(1)

# Import MCP components
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
except ImportError as e:
    print(f"Error importing MCP components: {e}")
    print("Please ensure MCP is installed: uv add mcp")
    exit(1)


class MonarchMCPServer:
    def __init__(self):
        self.mm: Optional[MonarchMoney] = None
        self.server = Server("monarch-money", version="1.0.0")
        self.setup_handlers()

    def setup_handlers(self):
        @self.server.list_resources()
        async def handle_list_resources() -> list[types.Resource]:
            """List available financial data resources."""
            return [
                types.Resource(
                    uri="monarch://accounts",
                    name="Account Information",
                    description="All linked accounts in Monarch Money",
                    mimeType="application/json",
                ),
                types.Resource(
                    uri="monarch://transactions/recent",
                    name="Recent Transactions",
                    description="Last 100 transactions",
                    mimeType="application/json",
                ),
                types.Resource(
                    uri="monarch://budgets",
                    name="Budget Information", 
                    description="All budgets with actual vs target amounts",
                    mimeType="application/json",
                ),
                types.Resource(
                    uri="monarch://cashflow/summary",
                    name="Cashflow Summary",
                    description="Income, expenses, and savings summary",
                    mimeType="application/json",
                ),
            ]

        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read specific financial data resource."""
            if not await self._ensure_logged_in():
                raise Exception("Failed to authenticate with Monarch Money")

            try:
                if uri == "monarch://accounts":
                    data = await self.mm.get_accounts()
                    return json.dumps(data, indent=2, default=str)
                
                elif uri == "monarch://transactions/recent":
                    data = await self.mm.get_transactions()
                    return json.dumps(data, indent=2, default=str)
                
                elif uri == "monarch://budgets":
                    data = await self.mm.get_budgets()
                    return json.dumps(data, indent=2, default=str)
                
                elif uri == "monarch://cashflow/summary":
                    data = await self.mm.get_cashflow_summary()
                    return json.dumps(data, indent=2, default=str)
                
                else:
                    raise ValueError(f"Unknown resource URI: {uri}")
                    
            except Exception as e:
                raise Exception(f"Error retrieving resource {uri}: {str(e)}")

        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List available financial analysis tools (read-only)."""
            return [
                types.Tool(
                    name="get_transactions",
                    description="Get transactions with optional date range filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "format": "date",
                                "description": "Start date for transaction search (YYYY-MM-DD)"
                            },
                            "end_date": {
                                "type": "string", 
                                "format": "date",
                                "description": "End date for transaction search (YYYY-MM-DD)"
                            },
                            "account_id": {
                                "type": "string",
                                "description": "Optional account ID to filter transactions"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of transactions to return (default: 100)"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="get_account_details",
                    description="Get detailed information about specific accounts",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_id": {
                                "type": "string",
                                "description": "Specific account ID to get details for"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="get_cashflow_analysis",
                    description="Get detailed cashflow analysis by category and time period",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "format": "date", 
                                "description": "Start date for analysis (YYYY-MM-DD)"
                            },
                            "end_date": {
                                "type": "string",
                                "format": "date",
                                "description": "End date for analysis (YYYY-MM-DD)"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="search_transactions",
                    description="Search transactions by description or merchant",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search term for transaction description or merchant"
                            },
                            "start_date": {
                                "type": "string",
                                "format": "date",
                                "description": "Start date for search (YYYY-MM-DD)"
                            },
                            "end_date": {
                                "type": "string",
                                "format": "date", 
                                "description": "End date for search (YYYY-MM-DD)"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="get_categories",
                    description="Get all transaction categories configured in the account",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="get_institutions",
                    description="Get all financial institutions linked to Monarch Money",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any] | None) -> list[types.TextContent]:
            """Handle tool calls for financial operations (read-only)."""
            if not await self._ensure_logged_in():
                return [types.TextContent(
                    type="text",
                    text="Error: Failed to authenticate with Monarch Money"
                )]

            try:
                if name == "get_transactions":
                    result = await self._handle_get_transactions(arguments or {})
                elif name == "get_account_details":
                    result = await self._handle_get_account_details(arguments or {})
                elif name == "get_cashflow_analysis":
                    result = await self._handle_get_cashflow_analysis(arguments or {})
                elif name == "search_transactions":
                    result = await self._handle_search_transactions(arguments or {})
                elif name == "get_categories":
                    result = await self._handle_get_categories(arguments or {})
                elif name == "get_institutions":
                    result = await self._handle_get_institutions(arguments or {})
                else:
                    result = f"Unknown tool: {name}"
                
                return [types.TextContent(type="text", text=result)]
                
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=f"Error executing {name}: {str(e)}"
                )]

    async def _ensure_logged_in(self) -> bool:
        """Ensure we're logged into Monarch Money - EXACTLY like debug script."""
        if self.mm is None:
            self.mm = MonarchMoney()  # Use default constructor like debug script
            
            # Check for session file (like debug script)
            session_file = ".mm/mm_session.pickle"
            if os.path.exists(session_file):
                print(f"💾 Session file exists: {session_file}")
                try:
                    await self.mm.load_session(session_file)
                    print("✓ Session loaded successfully")
                    return True
                except Exception as e:
                    print(f"❌ Session load failed: {e}")
                    # Continue to fresh login below
            else:
                print("ℹ No session file found, attempting fresh login...")
            
            # Fresh login (like debug script)
            email = os.getenv("MONARCH_EMAIL")
            password = os.getenv("MONARCH_PASSWORD")
            mfa_secret = os.getenv("MONARCH_MFA_SECRET")
            
            if not email or not password:
                print("Error: MONARCH_EMAIL and MONARCH_PASSWORD environment variables must be set")
                return False
                
            try:
                await self.mm.login(
                    email=email,
                    password=password,
                    save_session=True,
                    mfa_secret_key=mfa_secret
                )
                print("✓ Fresh login successful")
                return True
            except RequireMFAException:
                print("Error: MFA required but no secret key provided. Set MONARCH_MFA_SECRET environment variable.")
                return False
            except Exception as e:
                print(f"Login failed: {str(e)}")
                return False
        return True

    async def _handle_get_transactions(self, arguments: Dict[str, Any]) -> str:
        """Handle get_transactions tool call - UPDATED for new API."""
        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")
        account_id = arguments.get("account_id")
        limit = arguments.get("limit", 100)
        
        # Convert single account_id to account_ids list if provided
        account_ids = None
        if account_id:
            account_ids = [account_id]
        
        # Updated API call with new parameter names
        transactions = await self.mm.get_transactions(
            start_date=start_date,
            end_date=end_date,
            account_ids=account_ids,  # Changed from account_id to account_ids
            limit=limit
        )
        
        return json.dumps(transactions, indent=2, default=str)

    async def _handle_get_account_details(self, arguments: Dict[str, Any]) -> str:
        """Handle get_account_details tool call."""
        account_id = arguments.get("account_id")
        
        if account_id:
            # Get specific account
            accounts_data = await self.mm.get_accounts()
            accounts = accounts_data.get("accounts", [])
            account = next((acc for acc in accounts if acc.get("id") == account_id), None)
            if account:
                # Get additional details like holdings if it's an investment account
                account_type = account.get("type", {}).get("name", "")
                if "brokerage" in account_type.lower() or "investment" in account_type.lower():
                    try:
                        holdings = await self.mm.get_account_holdings(account_id)
                        account["holdings"] = holdings
                    except Exception as e:
                        print(f"Could not get holdings for account {account_id}: {e}")
                
                result = account
            else:
                result = {"error": f"Account with ID {account_id} not found"}
        else:
            result = await self.mm.get_accounts()
            
        return json.dumps(result, indent=2, default=str)

    async def _handle_get_cashflow_analysis(self, arguments: Dict[str, Any]) -> str:
        """Handle get_cashflow_analysis tool call."""
        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")
        
        try:
            # Try to get detailed cashflow data
            cashflow_data = await self.mm.get_cashflow(
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            print(f"Could not get detailed cashflow: {e}")
            cashflow_data = None
        
        try:
            # Get cashflow summary
            summary = await self.mm.get_cashflow_summary()
        except Exception as e:
            print(f"Could not get cashflow summary: {e}")
            summary = None
        
        result = {
            "summary": summary,
            "detailed_cashflow": cashflow_data,
            "date_range": {
                "start": start_date,
                "end": end_date
            }
        }
        
        return json.dumps(result, indent=2, default=str)

    async def _handle_search_transactions(self, arguments: Dict[str, Any]) -> str:
        """Handle search_transactions tool call."""
        query = arguments["query"]
        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")
        
        # Get transactions and filter by query
        transactions_data = await self.mm.get_transactions(
            start_date=start_date,
            end_date=end_date,
            limit=1000  # Get more transactions for searching
        )
        
        # Extract transactions list from response
        transactions = transactions_data.get("allTransactions", {}).get("results", [])
        
        # Filter transactions based on query
        filtered_transactions = []
        query_lower = query.lower()
        
        for transaction in transactions:
            description = transaction.get("description", "").lower()
            merchant_name = ""
            if transaction.get("merchant"):
                merchant_name = transaction.get("merchant", {}).get("name", "").lower()
            
            if query_lower in description or query_lower in merchant_name:
                filtered_transactions.append(transaction)
        
        result = {
            "query": query,
            "matches_found": len(filtered_transactions),
            "transactions": filtered_transactions
        }
        
        return json.dumps(result, indent=2, default=str)

    async def _handle_get_categories(self, arguments: Dict[str, Any]) -> str:
        """Handle get_categories tool call."""
        try:
            categories = await self.mm.get_transaction_categories()
        except Exception as e:
            categories = {"error": f"Could not get categories: {e}"}
        
        try:
            category_groups = await self.mm.get_transaction_category_groups()
        except Exception as e:
            category_groups = {"error": f"Could not get category groups: {e}"}
        
        result = {
            "categories": categories,
            "category_groups": category_groups
        }
        
        return json.dumps(result, indent=2, default=str)

    async def _handle_get_institutions(self, arguments: Dict[str, Any]) -> str:
        """Handle get_institutions tool call."""
        institutions = await self.mm.get_institutions()
        return json.dumps(institutions, indent=2, default=str)

    async def run(self):
        """Run the MCP server."""
        print("🚀 Starting Monarch Money MCP Server (Read-Only Mode)...")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point."""
    server = MonarchMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
