import io
import os

import httpx
import pymupdf
import yaml
from fastmcp import FastMCP
from fastmcp.server.providers.openapi import MCPType, RouteMap

from auth import API_BASE, KlaraAuth

_ALLOW_DELETE = os.environ.get("ALLOW_DELETE", "").lower() in ("1", "true", "yes")

_TOOL_NAMES = {
    ("GET", "/epost/v2/letters"): "list_letters",
    ("GET", "/epost/v2/letters/search"): "search_letters",
    ("GET", "/epost/v2/letters/{letter-id}"): "get_letter",
    ("DELETE", "/epost/v2/letters/{letter-id}"): "delete_letter",
    ("GET", "/epost/v2/letters/{letter-id}/content"): "get_letter_content",
    ("GET", "/epost/v2/letters/{letter-id}/thumbnail"): "get_letter_thumbnail",
    ("GET", "/epost/v2/letters/inbox/count"): "get_inbox_count",
    ("GET", "/epost/v2/letters/deleted"): "list_deleted_letters",
    ("POST", "/epost/v2/letters/read"): "mark_letters_read",
    ("PATCH", "/epost/v2/letters/{letter-id}/archive"): "archive_letter",
    ("POST", "/epost/v2/letters/{letter-id}/restore"): "restore_letter",
    ("GET", "/epost/v2/archives/directories"): "list_archive_folders",
    ("GET", "/epost/v2/archives/letters"): "list_archive_letters",
    ("POST", "/epost/v2/deliveries"): "create_delivery",
    ("GET", "/epost/v2/deliveries/{delivery-id}/status"): "get_delivery_status",
    ("POST", "/epost/v2/synchronous-deliveries"): "create_sync_delivery",
    ("POST", "/epost/v2/single-file-deliveries"): "create_single_file_delivery",
    ("POST", "/epost/preview/delivery-channels"): "preview_delivery_channels",
    ("GET", "/epost/preview/delivery-channels/{preview-id}/status"): "get_channel_preview_status",
    ("POST", "/epost/preview/delivery-prices"): "preview_delivery_prices",
    ("GET", "/epost/preview/delivery-prices/{preview-id}/status"): "get_price_preview_status",
}


def _rename_tools(route, component) -> None:
    if not _ALLOW_DELETE and route.method.upper() == "DELETE":
        component.mcp_type = MCPType.EXCLUDE
        return
    key = (route.method.upper(), route.path)
    if key in _TOOL_NAMES:
        component.name = _TOOL_NAMES[key]


def _load_spec() -> dict:
    """Fetch and parse the Klara OpenAPI spec (YAML)."""

    class _Loader(yaml.SafeLoader):
        pass

    # The spec contains date-like strings that trip up YAML's timestamp resolver
    for key in list(_Loader.yaml_implicit_resolvers):
        _Loader.yaml_implicit_resolvers[key] = [
            (tag, regexp)
            for tag, regexp in _Loader.yaml_implicit_resolvers[key]
            if tag != "tag:yaml.org,2002:timestamp"
        ]

    raw = httpx.get(f"{API_BASE}/openapi?query=All", timeout=30).text
    return yaml.load(raw, Loader=_Loader)


auth = KlaraAuth(
    username=os.environ.get("KLARA_USERNAME", ""),
    password=os.environ.get("KLARA_PASSWORD", ""),
)

client = httpx.AsyncClient(base_url=API_BASE, auth=auth, timeout=30)

mcp = FastMCP.from_openapi(
    openapi_spec=_load_spec(),
    client=client,
    name="Swiss ePost",
    route_maps=[
        # Letterbox: list, search, read, delete, archive, restore letters
        RouteMap(tags={"ePost Digital Letterbox"}, mcp_type=MCPType.TOOL),
        # Archive / Storage: folders and stored documents
        RouteMap(tags={"ePost eArchive"}, mcp_type=MCPType.TOOL),
        # Delivery: send documents and check status
        RouteMap(tags={"ePost Communication Platform Delivery"}, mcp_type=MCPType.TOOL),
        # Preview: check delivery channels and pricing before sending
        RouteMap(tags={"ePost Communication Platform Preview Services"}, mcp_type=MCPType.TOOL),
        # Exclude everything else
        RouteMap(mcp_type=MCPType.EXCLUDE),
    ],
    mcp_component_fn=_rename_tools,
    validate_output=False,
)


@mcp.tool()
async def read_letter(letter_id: str) -> str:
    """Read the text content of a letter (PDF). Returns the extracted text from all pages."""
    resp = await client.get(f"/epost/v2/letters/{letter_id}/content")
    resp.raise_for_status()
    doc = pymupdf.open(stream=resp.content, filetype="pdf")
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n--- Page Break ---\n".join(pages)
