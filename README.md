# Monarch Money MCP Server + HTTP Proxy

Read-only access to [Monarch Money](https://www.monarchmoney.com/) financial data via two interfaces:

- **MCP Server** — stdio-based, for local use with Claude Desktop / Claude Code
- **HTTP Proxy** — FastAPI REST API, for remote access over Tailscale or any network

> **Note:** This is a personal project, not affiliated with Monarch Money. Built for learning about spending patterns and projections. All access is read-only.

## Important: Upstream Library Fix

The original `monarchmoney` Python package (by hammem) is abandoned and broken — Monarch rebranded their API from `api.monarchmoney.com` to `api.monarch.com`, causing HTTP 525 errors. This project uses [`monarchmoneycommunity`](https://github.com/bradleyseanf/monarchmoneycommunity), the maintained community fork.

## Features

- **Read-only access** to all Monarch Money accounts
- **Transaction analysis** with date filtering and search
- **Budget tracking** and cashflow analysis
- **Account details** including investment holdings
- **Secure authentication** with MFA/TOTP support
- **Session persistence** to minimize re-authentication
- **HTTP proxy** for remote access from any device on your network

## Installation

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- A Monarch Money account

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rmarji/monarch-mcp-server.git
   cd monarch-mcp-server
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Configure credentials:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env`:
   ```
   MONARCH_EMAIL=your-email@example.com
   MONARCH_PASSWORD=your-monarch-password
   MONARCH_MFA_SECRET=your-totp-secret-key
   ```

   The `MONARCH_MFA_SECRET` is the base32 TOTP secret from your authenticator app setup. This is required if your account has 2FA enabled (Monarch may require it by default).

## Usage

### HTTP Proxy (Remote Access)

Start the FastAPI proxy:
```bash
uv run python monarch_http_proxy.py
```

This binds to `0.0.0.0:8765` and is accessible from any device on your network (e.g., over Tailscale).

#### Endpoints

| Method | Path | Query Params | Description |
|--------|------|-------------|-------------|
| GET | `/health` | — | Status and auth check |
| GET | `/accounts` | — | All linked accounts |
| GET | `/accounts/{id}` | — | Account details (includes holdings for investment accounts) |
| GET | `/transactions` | `start_date`, `end_date`, `account_id`, `limit` | Filtered transactions |
| GET | `/transactions/search` | `q` (required), `start_date`, `end_date` | Search by description/merchant |
| GET | `/cashflow` | `start_date`, `end_date` | Cashflow summary and details |
| GET | `/categories` | — | Transaction categories |

#### Examples

```bash
curl http://localhost:8765/health
curl http://localhost:8765/accounts
curl http://localhost:8765/transactions?limit=5
curl http://localhost:8765/transactions?start_date=2026-01-01&end_date=2026-01-31
curl "http://localhost:8765/transactions/search?q=grocery"
curl http://localhost:8765/cashflow?start_date=2026-01-01&end_date=2026-03-01
```

The port can be changed via `MONARCH_PROXY_PORT` in `.env` (default: 8765).

### MCP Server (Claude Desktop / Claude Code)

Start the MCP server:
```bash
uv run python run_server.py
```

#### Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "monarch-money": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/monarch-mcp-server", "python", "run_server.py"],
      "env": {
        "MONARCH_EMAIL": "your-email@example.com",
        "MONARCH_PASSWORD": "your-password",
        "MONARCH_MFA_SECRET": "your-totp-secret"
      }
    }
  }
}
```

#### MCP Resources

- `monarch://accounts` — All linked accounts
- `monarch://transactions/recent` — Last 100 transactions
- `monarch://budgets` — Budget information with actual vs target
- `monarch://cashflow/summary` — Income, expenses, and savings summary

#### MCP Tools

- **get_transactions** — Transactions with date range filtering
- **get_account_details** — Detailed account info including holdings
- **get_cashflow_analysis** — Cashflow analysis by category and time period
- **search_transactions** — Search by description or merchant
- **get_categories** — All transaction categories
- **get_institutions** — Linked financial institutions

## Project Structure

```
monarch-mcp-server/
├── monarch_http_proxy.py    # FastAPI HTTP proxy for remote access
├── monarch_mcp_server.py    # MCP server implementation
├── run_server.py            # MCP server launcher
├── debug_server.py          # Authentication debugging
├── test_api.py              # API connection testing
├── tests/
│   └── test_monarch_mcp_server.py
├── pyproject.toml
├── .env.example
└── .gitignore
```

## Security

- **No write operations** — entirely read-only
- **Credentials stay local** — `.env` and session files are gitignored
- **Session caching** — authenticates once, reuses session via `.mm/mm_session.pickle`
- **MFA/TOTP support** — auto-generates 2FA codes from your secret key
- **No auth on HTTP proxy** — relies on network isolation (Tailscale, private network, etc.)

## Troubleshooting

### HTTP 525 / Login Failures

If you see `HTTP Code 525`, you're likely using the abandoned `monarchmoney` package. This project requires `monarchmoneycommunity`:
```bash
uv remove monarchmoney
uv add monarchmoneycommunity
```

### MFA Required

Monarch Money may require 2FA even if you didn't explicitly enable it. Add `MONARCH_MFA_SECRET` to your `.env`.

### Stale Session

Delete the cached session to force a fresh login:
```bash
rm -rf .mm/
```

## Testing

```bash
uv sync --extra test
uv run pytest tests/ -v
```

## License

MIT License — see [LICENSE](LICENSE) for details.

## Disclaimer

This project is not affiliated with Monarch Money. Use at your own risk and ensure compliance with Monarch Money's terms of service.
