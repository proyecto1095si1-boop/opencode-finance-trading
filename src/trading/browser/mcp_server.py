from __future__ import annotations

import os
from typing import Any

from mcp.server import MCPServer

from trading.browser.binance_browser import BinanceBrowser


mcp = MCPServer("opencode-binance-browser")
browser = BinanceBrowser(
    profile_dir=os.getenv("BROWSER_PROFILE_DIR", ".browser-profile"),
    headless=os.getenv("BROWSER_HEADLESS", "false").lower() == "true",
    cdp_url=os.getenv("BROWSER_CDP_URL", ""),
)


@mcp.tool()
async def browser_start() -> dict[str, Any]:
    """Start the persistent Binance browser session for manual login."""
    return await browser.start()


@mcp.tool()
async def browser_navigate(url: str) -> dict[str, str]:
    """Navigate only within approved Binance domains."""
    return await browser.navigate(url)


@mcp.tool()
async def browser_snapshot() -> dict[str, Any]:
    """Read the current Binance page for prices, chart labels, and account UI state."""
    return await browser.snapshot()


@mcp.tool()
async def browser_wait(milliseconds: int = 1000) -> dict[str, Any]:
    """Wait briefly for Binance UI updates before taking a new snapshot."""
    return await browser.wait_for_page(milliseconds)


@mcp.tool()
async def browser_screenshot(filename: str = "artifacts/binance-page.png") -> dict[str, str]:
    """Save a screenshot as evidence before or after a reviewed action."""
    return await browser.screenshot(filename)


@mcp.tool()
async def browser_click(selector: str) -> dict[str, str]:
    """Click a reviewed page element by selector."""
    return await browser.click(selector)


@mcp.tool()
async def browser_fill(selector: str, value: str) -> dict[str, str]:
    """Fill a non-secret order or filter field in the Binance page."""
    return await browser.fill(selector, value)


@mcp.tool()
async def request_order_confirmation(description: str) -> dict[str, str]:
    """Create a confirmation barrier before any order-submission action."""
    return await browser.request_order_confirmation(description)


@mcp.tool()
async def confirm_order_action(confirmation: str) -> dict[str, str]:
    """Confirm a pending order action using its exact description."""
    return await browser.confirm_order_action(confirmation)


if __name__ == "__main__":
    mcp.run()