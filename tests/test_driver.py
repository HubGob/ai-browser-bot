"""Tests for BrowserDriver — requires Playwright browsers installed."""

import pytest

from ai_browser_bot.driver import BrowserDriver


@pytest.mark.asyncio
async def test_start_stop_lifecycle():
    driver = BrowserDriver()
    await driver.start(headless=True)
    assert driver.page is not None
    await driver.stop()
    # After stop, page property should raise
    with pytest.raises(RuntimeError, match="not started"):
        _ = driver.page


@pytest.mark.asyncio
async def test_goto_known_page():
    driver = BrowserDriver()
    await driver.start(headless=True)
    try:
        await driver.goto("https://example.com")
        title = await driver.page.title()
        assert title == "Example Domain"
    finally:
        await driver.stop()


@pytest.mark.asyncio
async def test_screenshot_creates_file(tmp_path):
    driver = BrowserDriver()
    await driver.start(headless=True)
    try:
        await driver.goto("https://example.com")
        dest = tmp_path / "shot.png"
        await driver.screenshot(str(dest))
        assert dest.exists()
        assert dest.stat().st_size > 0
    finally:
        await driver.stop()
