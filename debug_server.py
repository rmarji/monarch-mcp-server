#!/usr/bin/env python3
"""
Debug version of Monarch Money MCP Server with detailed logging
"""

import asyncio
import os
from dotenv import load_dotenv
from monarchmoney import MonarchMoney

async def debug_auth():
    """Debug authentication step by step."""
    print("🔍 Debug: Starting authentication test...")
    
    # Load environment
    load_dotenv()
    email = os.getenv("MONARCH_EMAIL")
    password = os.getenv("MONARCH_PASSWORD")
    mfa_secret = os.getenv("MONARCH_MFA_SECRET")
    
    print(f"📧 Email loaded: {'Yes' if email else 'No'}")
    print(f"🔐 Password loaded: {'Yes' if password else 'No'}")
    print(f"📱 MFA Secret loaded: {'Yes' if mfa_secret else 'No'}")
    
    mm = MonarchMoney()
    
    # Check for session file
    session_file = ".mm/mm_session.pickle"
    if os.path.exists(session_file):
        print(f"💾 Session file exists: {session_file}")
        try:
            await mm.load_session(session_file)
            print("✓ Session loaded successfully")
        except Exception as e:
            print(f"❌ Session load failed: {e}")
            return False
    else:
        print("ℹ No session file found, attempting fresh login...")
        try:
            await mm.login(
                email=email,
                password=password,
                save_session=True,
                mfa_secret_key=mfa_secret
            )
            print("✓ Fresh login successful")
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False
    
    # Test a simple API call
    try:
        institutions = await mm.get_institutions()
        print(f"✓ API test successful: Found {len(institutions.get('credentials', []))} credentials")
        return True
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_auth())
    if success:
        print("\n🎉 Authentication is working! Your MCP server should work now.")
    else:
        print("\n❌ Authentication failed. Check the error messages above.")
