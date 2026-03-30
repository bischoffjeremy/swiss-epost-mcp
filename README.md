<p align="center">
  <img src="logo.png" alt="Swiss ePost MCP" width="800">
</p>

# Swiss ePost MCP Server

MCP server for the Swiss Post digital letterbox (ePost) via the [Klara API](https://api.klara.ch/docs). Built with [FastMCP](https://gofastmcp.com/) and auto-generated from the official OpenAPI specification.

Allows AI agents to read, search, manage, and send digital letters through your Swiss ePost account.

## Tools

| Tool | Description |
|------|-------------|
| `list_letters` | List letters in inbox or sent folder |
| `search_letters` | Search letters by keyword |
| `get_letter` | Get letter metadata by ID |
| `read_letter` | Read letter text content (extracts text from PDF) |
| `get_letter_content` | Download letter content (raw PDF bytes) |
| `get_letter_thumbnail` | Get letter thumbnail image |
| `get_inbox_count` | Get unread letter count |
| `mark_letters_read` | Mark letters as read/unread |
| `delete_letter`\* | Delete a letter |
| `restore_letter` | Restore a deleted letter |
| `list_deleted_letters` | List deleted letters |
| `archive_letter` | Archive letter to storage |
| `list_archive_folders` | List storage folders |
| `list_archive_letters` | List letters in storage |
| `create_delivery` | Send documents |
| `create_sync_delivery` | Send documents (synchronous) |
| `get_delivery_status` | Check delivery status |
| `preview_delivery_channels` | Preview available delivery channels |
| `preview_delivery_prices` | Preview delivery pricing |

\* Disabled by default. Set `ALLOW_DELETE=true` to enable.

## Quick Start

### Docker (recommended)

```bash
cp .env.example .env
# Edit .env with your Klara credentials

docker compose up -d
```

The server runs on `http://localhost:8000/mcp/` (Streamable HTTP transport).

### Local

```bash
pip install .
export KLARA_USERNAME="your-email@example.com"
export KLARA_PASSWORD="your-password"
fastmcp run src.server:mcp --transport streamable-http --host 0.0.0.0 --port 8000
```

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|----------|
| `KLARA_USERNAME` | Your Klara account email | *required* |
| `KLARA_PASSWORD` | Your Klara account password | *required* |
| `KLARA_TENANT` | Tenant name (company) to use | Private account |
| `ALLOW_DELETE` | Enable delete endpoints (`true`/`false`) | `false` |

Authentication is handled automatically: the server discovers your tenant, generates a bearer token, and refreshes it when needed.

## MCP Client Configuration

Add to your MCP client config (e.g. Claude Desktop, VS Code):

```json
{
  "mcpServers": {
    "swiss-epost": {
      "url": "http://localhost:8000/mcp/"
    }
  }
}
```

## License

MIT
