"""Tests for DOMInspector."""

import pytest
from ai_browser_bot.driver import BrowserDriver
from ai_browser_bot.dom import DOMInspector


@pytest.mark.asyncio
async def test_snapshot_nonempty_on_example_com():
    driver = BrowserDriver()
    await driver.start(headless=True)
    try:
        await driver.goto("https://example.com")
        inspector = DOMInspector()
        snap = await inspector.snapshot(driver.page)
        assert len(snap) > 0
        assert "<h1" in snap or "<p" in snap
    finally:
        await driver.stop()


@pytest.mark.asyncio
async def test_snapshot_filters_scripts():
    driver = BrowserDriver()
    await driver.start(headless=True)
    try:
        await driver.goto("https://example.com")
        inspector = DOMInspector()
        snap = await inspector.snapshot(driver.page)
        # Should not contain raw script content
        assert "<script>" not in snap
    finally:
        await driver.stop()


@pytest.mark.asyncio
async def test_snapshot_respects_max_nodes():
    driver = BrowserDriver()
    await driver.start(headless=True)
    try:
        await driver.goto("https://example.com")
        inspector = DOMInspector(max_nodes=5)
        snap = await inspector.snapshot(driver.page)
        lines = [l for l in snap.split("\n") if l.strip()]
        assert len(lines) <= 5
    finally:
        await driver.stop()
