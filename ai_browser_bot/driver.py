"""Low-level Playwright browser driver."""

from __future__ import annotations

from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright


class BrowserDriver:
    """Manages a Playwright browser, context, and page lifecycle.

    Usage:
        driver = BrowserDriver()
        await driver.start(headless=True)
        await driver.goto("https://example.com")
        html = await driver.page.content()
        await driver.stop()
    """

    def __init__(self) -> None:
        self._playwright: Optional[any] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page

    async def start(self, headless: bool = True, slow_mo: float = 0) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=headless, slow_mo=slow_mo
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720}
        )
        self._page = await self._context.new_page()

    async def stop(self) -> None:
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._page = self._context = self._browser = self._playwright = None

    async def goto(self, url: str, wait_until: str = "domcontentloaded") -> None:
        await self.page.goto(url, wait_until=wait_until)

    async def screenshot(self, path: str) -> None:
        await self.page.screenshot(path=path)
