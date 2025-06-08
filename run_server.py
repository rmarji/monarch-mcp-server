#!/usr/bin/env python3
"""
Launch script for Monarch Money MCP Server
Works with both uv and regular Python environments
"""
import os
import sys
import asyncio
from pathlib import Path

# Ensure we're in the right directory
script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    env_file = script_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✓ Loaded environment variables from {env_file}")
    else:
        print("ℹ No .env file found, using system environment variables")
except ImportError:
    print("ℹ python-dotenv not installed, using system environment variables only")

# Verify required environment variables
required_vars = ["MONARCH_EMAIL", "MONARCH_PASSWORD"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"❌ Error: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please set these in your .env file or system environment")
    print("\nCreate a .env file with:")
    print("MONARCH_EMAIL=your-email@example.com")
    print("MONARCH_PASSWORD=your-monarch-password")
    print("MONARCH_MFA_SECRET=your-mfa-secret-key  # Optional but recommended")
    sys.exit(1)

def main():
    """Main entry point for the script."""
    # Import and run the server
    try:
        from monarch_mcp_server import main as server_main
        
        print("🚀 Starting Monarch Money MCP Server...")
        print(f"📧 Using email: {os.getenv('MONARCH_EMAIL')}")
        print(f"🔐 MFA Secret configured: {'Yes' if os.getenv('MONARCH_MFA_SECRET') else 'No'}")
        print(f"📁 Working directory: {os.getcwd()}")
        print("📊 Server ready for Claude Desktop connections...")
        
        asyncio.run(server_main())
        
    except ImportError as e:
        print(f"❌ Error importing monarch_mcp_server: {e}")
        print("Make sure monarch_mcp_server.py is in the same directory")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
