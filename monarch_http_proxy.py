#!/usr/bin/env python3
"""
Monarch Money HTTP Proxy — FastAPI REST wrapper for remote access over Tailscale.

Run: uv run python monarch_http_proxy.py
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from monarchmoney import MonarchMoney, RequireMFAException

load_dotenv()

# --- Monarch Money client (singleton) ---

mm: Optional[MonarchMoney] = None
authenticated = False


async def ensure_logged_in() -> MonarchMoney:
    """Authenticate with Monarch Money, reusing cached session when possible."""
    global mm, authenticated

    if mm is not None and authenticated:
        return mm

    mm = MonarchMoney()
    session_file = ".mm/mm_session.pickle"

    # Try cached session first (load_session is synchronous in community fork)
    if os.path.exists(session_file):
        try:
            mm.load_session(session_file)
            authenticated = True
            print("Session loaded from cache")
            return mm
        except Exception as e:
            print(f"Session load failed: {e}")

    email = os.getenv("MONARCH_EMAIL")
    password = os.getenv("MONARCH_PASSWORD")
    mfa_secret = os.getenv("MONARCH_MFA_SECRET")

    if not email or not password:
        raise RuntimeError("MONARCH_EMAIL and MONARCH_PASSWORD must be set in .env")

    # Use _login_user directly to bypass the library's own saved-session check
    await mm._login_user(email, password, mfa_secret)
    mm.save_session(session_file)
    authenticated = True
    print("Fresh login successful")
    return mm


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Authenticate on startup."""
    try:
        await ensure_logged_in()
        print(f"Proxy ready on port {os.getenv('MONARCH_PROXY_PORT', '8765')}")
    except Exception as e:
        print(f"WARNING: startup auth failed ({e}) — will retry on first request")
    yield


# --- FastAPI app ---

app = FastAPI(title="Monarch Money Proxy", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "authenticated": authenticated}


@app.get("/accounts")
async def get_accounts():
    client = await ensure_logged_in()
    return await client.get_accounts()


@app.get("/accounts/{account_id}")
async def get_account_details(account_id: str):
    client = await ensure_logged_in()
    accounts_data = await client.get_accounts()
    accounts = accounts_data.get("accounts", [])
    account = next((a for a in accounts if a.get("id") == account_id), None)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

    account_type = account.get("type", {}).get("name", "")
    if "brokerage" in account_type.lower() or "investment" in account_type.lower():
        try:
            account["holdings"] = await client.get_account_holdings(account_id)
        except Exception:
            pass

    return account


@app.get("/transactions")
async def get_transactions(
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    account_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=10000),
):
    client = await ensure_logged_in()
    account_ids = [account_id] if account_id else None
    return await client.get_transactions(
        start_date=start_date,
        end_date=end_date,
        account_ids=account_ids,
        limit=limit,
    )


@app.get("/transactions/search")
async def search_transactions(
    q: str = Query(..., description="Search term"),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
):
    client = await ensure_logged_in()
    data = await client.get_transactions(
        start_date=start_date,
        end_date=end_date,
        limit=1000,
    )
    transactions = data.get("allTransactions", {}).get("results", [])

    query_lower = q.lower()
    matches = [
        t
        for t in transactions
        if query_lower in t.get("description", "").lower()
        or query_lower in (t.get("merchant") or {}).get("name", "").lower()
    ]

    return {"query": q, "matches_found": len(matches), "transactions": matches}


@app.get("/cashflow")
async def get_cashflow(
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
):
    client = await ensure_logged_in()

    cashflow_data = None
    try:
        cashflow_data = await client.get_cashflow(
            start_date=start_date, end_date=end_date
        )
    except Exception:
        pass

    summary = None
    try:
        summary = await client.get_cashflow_summary()
    except Exception:
        pass

    return {
        "summary": summary,
        "detailed_cashflow": cashflow_data,
        "date_range": {"start": start_date, "end": end_date},
    }


@app.get("/categories")
async def get_categories():
    client = await ensure_logged_in()
    return await client.get_transaction_categories()


# --- Entry point ---

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("MONARCH_PROXY_PORT", "8765"))
    uvicorn.run(app, host="0.0.0.0", port=port)
