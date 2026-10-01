from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class BinanceBrowser:
    """Browser session used by the OpenCode MCP bridge.

    Login is intentionally interactive. Credentials are never accepted by this
    class and order submission requires an explicit confirmation token.
    """

    def __init__(self, profile_dir: str | None = None, headless: bool = False, cdp_url: str | None = None):
        self.profile_dir = Path(profile_dir or os.getenv("BROWSER_PROFILE_DIR", ".browser-profile")).resolve()
        self.headless = headless
        self.cdp_url = cdp_url or os.getenv("BROWSER_CDP_URL", "")
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.pending_confirmation: str | None = None
        self.order_action_authorized = False

    async def start(self) -> dict[str, Any]:
        from playwright.async_api import async_playwright

        self.playwright = await async_playwright().start()
        if self.cdp_url:
            self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_url)
            self.context = self.browser.contexts[0] if self.browser.contexts else await self.browser.new_context()
            self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            return {
                "started": True,
                "attached": True,
                "cdp_url": self.cdp_url,
                "url": self.page.url,
                "login": "use_existing_browser_session",
            }

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        requested_headless = self.headless
        display_available = bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))
        if not self.headless and not display_available:
            self.headless = True
        self.context = await self.playwright.chromium.launch_persistent_context(
            str(self.profile_dir),
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        return {
            "started": True,
            "url": self.page.url,
            "profile_dir": str(self.profile_dir),
            "headless": self.headless,
            "display_fallback": requested_headless is False and self.headless,
            "login": "manual_login_required" if self.headless else "manual_login_available",
        }

    async def navigate(self, url: str) -> dict[str, str]:
        self._require_page()
        if not url.startswith(("https://www.binance.com", "https://binance.com")):
            raise ValueError("Browser navigation is restricted to Binance domains.")
        await self.page.goto(url, wait_until="domcontentloaded")
        return {"url": self.page.url, "title": await self.page.title()}

    async def snapshot(self) -> dict[str, Any]:
        self._require_page()
        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "text": (await self.page.locator("body").inner_text())[:12000],
        }

    async def wait_for_page(self, milliseconds: int = 1000) -> dict[str, Any]:
        self._require_page()
        if milliseconds < 0 or milliseconds > 10000:
            raise ValueError("milliseconds must be between 0 and 10000")
        await self.page.wait_for_timeout(milliseconds)
        return {"url": self.page.url, "title": await self.page.title()}

    async def screenshot(self, filename: str = "artifacts/binance-page.png") -> dict[str, str]:
        self._require_page()
        target = Path(filename).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        await self.page.screenshot(path=str(target), full_page=False)
        return {"path": str(target), "url": self.page.url}

    async def click(self, selector: str) -> dict[str, str]:
        self._require_page()
        if self._is_order_action(selector):
            if not self.order_action_authorized:
                raise PermissionError("Order action blocked until exact explicit confirmation.")
            self.order_action_authorized = False
        await self.page.locator(selector).click()
        return {"clicked": selector, "url": self.page.url}

    async def fill(self, selector: str, value: str) -> dict[str, str]:
        self._require_page()
        await self.page.locator(selector).fill(value)
        return {"filled": selector}

    async def request_order_confirmation(self, description: str) -> dict[str, str]:
        self._require_page()
        self.pending_confirmation = description
        return {
            "status": "confirmation_required",
            "description": description,
            "message": "The order form must be reviewed and confirmed explicitly before submission.",
        }

    async def confirm_order_action(self, confirmation: str) -> dict[str, str]:
        self._require_page()
        if not self.pending_confirmation:
            raise ValueError("No pending order action exists.")
        if confirmation != self.pending_confirmation:
            raise ValueError("Confirmation text does not match the pending order.")
        self.pending_confirmation = None
        self.order_action_authorized = True
        return {"status": "confirmed", "message": "Order action may now be submitted by a separate, reviewed browser step."}

    @staticmethod
    def _is_order_action(selector: str) -> bool:
        normalized = selector.lower()
        return any(
            token in normalized
            for token in ("buy", "sell", "submit", "place-order", "open-order", "close-position")
        )

    def _require_page(self) -> None:
        if self.page is None:
            raise RuntimeError("Browser is not started. Call browser_start first.")