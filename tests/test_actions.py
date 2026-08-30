"""Tests for ActionExecutor."""

import pytest
from ai_browser_bot.driver import BrowserDriver
from ai_browser_bot.actions import ActionExecutor, Action


@pytest.mark.asyncio
async def test_click_on_example_com():
    driver = BrowserDriver()
    await driver.start(headless=True)
    try:
        await driver.goto("https://example.com")
        ex = ActionExecutor(driver)
        # example.com has no interactive elements, so this should error gracefully
        result = await ex.execute(Action(type="click", target="button"))
        assert result["status"] == "error"  # no such button
    finally:
        await driver.stop()


@pytest.mark.asyncio
async def test_navigate_action():
    driver = BrowserDriver()
    await driver.start(headless=True)
    try:
        ex = ActionExecutor(driver)
        result = await ex.execute(Action(type="navigate", target="https://example.com"))
        assert result["status"] == "ok"
        assert result["title"] == "Example Domain"
    finally:
        await driver.stop()


@pytest.mark.asyncio
async def test_screenshot_action(tmp_path):
    driver = BrowserDriver()
    await driver.start(headless=True)
    try:
        await driver.goto("https://example.com")
        ex = ActionExecutor(driver)
        dest = tmp_path / "out.png"
        result = await ex.execute(Action(type="screenshot", target=str(dest)))
        assert result["status"] == "ok"
        assert dest.exists()
    finally:
        await driver.stop()


@pytest.mark.asyncio
async def test_wait_action():
    driver = BrowserDriver()
    await driver.start(headless=True)
    try:
        ex = ActionExecutor(driver)
        result = await ex.execute(Action(type="wait", wait_seconds=0.1))
        assert result["status"] == "ok"
        assert result["seconds"] == 0.1
    finally:
        await driver.stop()
