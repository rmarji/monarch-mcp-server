#!/usr/bin/env python3
"""
Simple test script to verify Monarch Money API is working
"""
import asyncio
import os
import json
from dotenv import load_dotenv
from monarchmoney import MonarchMoney

# Load environment variables
load_dotenv()

async def test_monarch_api():
    """Test basic Monarch Money API functionality."""
    mm = MonarchMoney()
    
    try:
        # Try to load saved session first
        await mm.load_session()
        print("✓ Loaded saved session")
    except:
        print("ℹ No saved session, attempting login...")
        
        email = os.getenv("MONARCH_EMAIL")
        password = os.getenv("MONARCH_PASSWORD")
        mfa_secret = os.getenv("MONARCH_MFA_SECRET")
        
        if not email or not password:
            print("❌ Missing MONARCH_EMAIL or MONARCH_PASSWORD environment variables")
            return
            
        try:
            await mm.login(
                email=email,
                password=password,
                save_session=True,
                mfa_secret_key=mfa_secret
            )
            print("✓ Login successful")
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return
    
    try:
        # Test basic API calls
        print("\n🧪 Testing API calls...")
        
        # Get accounts
        accounts = await mm.get_accounts()
        print(f"✓ Accounts: Found {len(accounts.get('accounts', []))} accounts")
        
        # Get recent transactions (using new API)
        transactions = await mm.get_transactions(
            start_date="2025-03-01",
            end_date="2025-05-30",
            limit=10
        )
        print(f"✓ Transactions: Retrieved {len(transactions.get('allTransactions', {}).get('results', []))} transactions")
        
        # Test cashflow
        try:
            cashflow_summary = await mm.get_cashflow_summary()
            print(f"✓ Cashflow summary: Retrieved successfully")
        except Exception as e:
            print(f"⚠️ Cashflow summary failed: {e}")
        
        print("\n🎉 API test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_monarch_api())
    if success:
        print("\n✅ Your Monarch Money API connection is working!")
        print("You can now restart your MCP server and try the budget analysis again.")
    else:
        print("\n❌ There are still issues with the API connection.")
        print("Please check your credentials and network connection.")
