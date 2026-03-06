"""Entry point for the modelmux MCP server."""

from modelmux.server import mcp


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
