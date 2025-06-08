#!/usr/bin/env python3
"""
Unit tests for Monarch Money MCP Server
"""

import asyncio
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from mcp import types

# Import the server class
from monarch_mcp_server import MonarchMCPServer


class TestMonarchMCPServer:
    """Test cases for MonarchMCPServer class."""

    @pytest.fixture
    def server(self):
        """Create a MonarchMCPServer instance for testing."""
        return MonarchMCPServer()

    @pytest.fixture
    def mock_monarch_money(self):
        """Create a mock MonarchMoney instance."""
        mock_mm = AsyncMock()
        mock_mm.get_accounts.return_value = {
            "accounts": [
                {"id": "acc1", "name": "Checking", "balance": 1000.0},
                {"id": "acc2", "name": "Savings", "balance": 5000.0}
            ]
        }
        mock_mm.get_transactions.return_value = {
            "allTransactions": {
                "results": [
                    {"id": "txn1", "description": "Coffee Shop", "amount": -4.50},
                    {"id": "txn2", "description": "Salary", "amount": 3000.0}
                ]
            }
        }
        mock_mm.get_budgets.return_value = {
            "budgets": [
                {"category": "Food", "budgeted": 500, "actual": 450}
            ]
        }
        mock_mm.get_cashflow_summary.return_value = {
            "income": 3000,
            "expenses": 2500,
            "net": 500
        }
        return mock_mm

    def test_server_initialization(self, server):
        """Test that server initializes correctly."""
        assert server.mm is None
        assert server.server.name == "monarch-money"
        assert server.server.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_list_resources(self, server):
        """Test that list_resources returns expected resources."""
        # Get the handler function
        handler = server.server._resource_handlers.list_handler
        resources = await handler()
        
        assert len(resources) == 4
        resource_uris = [r.uri for r in resources]
        assert "monarch://accounts" in resource_uris
        assert "monarch://transactions/recent" in resource_uris
        assert "monarch://budgets" in resource_uris
        assert "monarch://cashflow/summary" in resource_uris

    @pytest.mark.asyncio
    async def test_list_tools(self, server):
        """Test that list_tools returns expected tools."""
        # Get the handler function
        handler = server.server._tool_handlers.list_handler
        tools = await handler()
        
        assert len(tools) == 6
        tool_names = [t.name for t in tools]
        expected_tools = [
            "get_transactions",
            "get_account_details", 
            "get_cashflow_analysis",
            "search_transactions",
            "get_categories",
            "get_institutions"
        ]
        for tool in expected_tools:
            assert tool in tool_names

    @pytest.mark.asyncio
    async def test_read_resource_accounts(self, server, mock_monarch_money):
        """Test reading accounts resource."""
        server.mm = mock_monarch_money
        
        # Mock the authentication check
        with patch.object(server, '_ensure_logged_in', return_value=True):
            handler = server.server._resource_handlers.read_handler
            result = await handler("monarch://accounts")
            
            # Verify the result is valid JSON
            data = json.loads(result)
            assert "accounts" in data
            assert len(data["accounts"]) == 2
            mock_monarch_money.get_accounts.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_resource_invalid_uri(self, server, mock_monarch_money):
        """Test reading invalid resource URI."""
        server.mm = mock_monarch_money
        
        with patch.object(server, '_ensure_logged_in', return_value=True):
            handler = server.server._resource_handlers.read_handler
            
            with pytest.raises(Exception) as exc_info:
                await handler("monarch://invalid")
            
            assert "Unknown resource URI" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authentication_failure(self, server):
        """Test behavior when authentication fails."""
        with patch.object(server, '_ensure_logged_in', return_value=False):
            handler = server.server._resource_handlers.read_handler
            
            with pytest.raises(Exception) as exc_info:
                await handler("monarch://accounts")
            
            assert "Failed to authenticate" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch.dict(os.environ, {
        'MONARCH_EMAIL': 'test@example.com',
        'MONARCH_PASSWORD': 'testpass',
        'MONARCH_MFA_SECRET': 'testsecret'
    })
    async def test_ensure_logged_in_with_env_vars(self, server):
        """Test authentication with environment variables."""
        mock_mm = AsyncMock()
        mock_mm.login = AsyncMock()
        
        with patch('monarch_mcp_server.MonarchMoney', return_value=mock_mm):
            with patch('os.path.exists', return_value=False):
                result = await server._ensure_logged_in()
                
                assert result is True
                assert server.mm == mock_mm
                mock_mm.login.assert_called_once_with(
                    email='test@example.com',
                    password='testpass',
                    save_session=True,
                    mfa_secret_key='testsecret'
                )

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    async def test_ensure_logged_in_missing_credentials(self, server):
        """Test authentication failure with missing credentials."""
        result = await server._ensure_logged_in()
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_get_transactions(self, server, mock_monarch_money):
        """Test get_transactions tool handler."""
        server.mm = mock_monarch_money
        
        result = await server._handle_get_transactions({
            "start_date": "2025-01-01",
            "end_date": "2025-01-31", 
            "limit": 10
        })
        
        data = json.loads(result)
        assert "allTransactions" in data
        mock_monarch_money.get_transactions.assert_called_once_with(
            start_date="2025-01-01",
            end_date="2025-01-31",
            account_ids=None,
            limit=10
        )

    @pytest.mark.asyncio
    async def test_handle_search_transactions(self, server, mock_monarch_money):
        """Test search_transactions tool handler."""
        server.mm = mock_monarch_money
        
        result = await server._handle_search_transactions({
            "query": "coffee",
            "start_date": "2025-01-01"
        })
        
        data = json.loads(result)
        assert "query" in data
        assert "matches_found" in data
        assert "transactions" in data
        assert data["query"] == "coffee"

    @pytest.mark.asyncio
    async def test_call_tool_success(self, server, mock_monarch_money):
        """Test successful tool call."""
        server.mm = mock_monarch_money
        
        with patch.object(server, '_ensure_logged_in', return_value=True):
            handler = server.server._tool_handlers.call_handler
            result = await handler("get_transactions", {"limit": 5})
            
            assert len(result) == 1
            assert result[0].type == "text"
            # Should be valid JSON
            json.loads(result[0].text)

    @pytest.mark.asyncio
    async def test_call_tool_auth_failure(self, server):
        """Test tool call when authentication fails."""
        with patch.object(server, '_ensure_logged_in', return_value=False):
            handler = server.server._tool_handlers.call_handler
            result = await handler("get_transactions", {})
            
            assert len(result) == 1
            assert result[0].type == "text"
            assert "Failed to authenticate" in result[0].text

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, server, mock_monarch_money):
        """Test calling unknown tool."""
        server.mm = mock_monarch_money
        
        with patch.object(server, '_ensure_logged_in', return_value=True):
            handler = server.server._tool_handlers.call_handler
            result = await handler("unknown_tool", {})
            
            assert len(result) == 1
            assert "Unknown tool" in result[0].text


class TestEnvironmentSetup:
    """Test environment and configuration setup."""

    def test_required_imports(self):
        """Test that all required modules can be imported."""
        try:
            from monarchmoney import MonarchMoney
            from mcp.server import Server
            from mcp import types
            assert True
        except ImportError:
            pytest.fail("Required dependencies not available")

    @patch.dict(os.environ, {'MONARCH_EMAIL': 'test@example.com', 'MONARCH_PASSWORD': 'pass'})
    def test_environment_variables_present(self):
        """Test that environment variables are accessible."""
        assert os.getenv('MONARCH_EMAIL') == 'test@example.com'
        assert os.getenv('MONARCH_PASSWORD') == 'pass'


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])