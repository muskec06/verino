"""MCP server exposing the CLI functions as tools (``verino mcp``)."""

from verino.mcp.server import build_server, check_hw, list_boards, render_hw, solve_pins

__all__ = ["build_server", "check_hw", "list_boards", "render_hw", "solve_pins"]
