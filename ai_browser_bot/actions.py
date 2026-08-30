"""Action types and executor — translates decisions into Playwright calls."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from ai_browser_bot.driver import BrowserDriver

# ---------------------------------------------------------------------------
# Action schemas (Pydantic models for structured LLM output)
# ---------------------------------------------------------------------------

ActionType = Literal["click", "type", "navigate", "scroll", "screenshot", "wait"]


class Action(BaseModel):
    """A single browser action to execute."""

    type: ActionType
    target: Optional[str] = Field(
        default=None,
        description="CSS selector, URL, or element description",
    )
    text: Optional[str] = Field(
        default=None,
        description="Text to type (for 'type' action)",
    )
    direction: Optional[str] = Field(
        default=None,
        description="scroll direction: up, down, left, right",
    )
    amount: Optional[int] = Field(
        default=None,
        description="scroll amount in pixels",
    )
    wait_seconds: Optional[float] = Field(
        default=None,
        description="seconds to wait (for 'wait' action)",
    )


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


class ActionExecutor:
    """Executes structured Action objects on a BrowserDriver's page."""

    def __init__(self, driver: BrowserDriver) -> None:
        self.driver = driver

    async def execute(self, action: Action) -> Dict[str, Any]:
        """Run an action and return a result dict."""
        match action.type:
            case "click":
                return await self._click(action)
            case "type":
                return await self._type(action)
            case "navigate":
                return await self._navigate(action)
            case "scroll":
                return await self._scroll(action)
            case "screenshot":
                return await self._screenshot(action)
            case "wait":
                return await self._wait(action)
            case _:
                return {"status": "error", "message": f"unknown action: {action.type}"}

    async def _click(self, action: Action) -> Dict[str, Any]:
        if not action.target:
            return {"status": "error", "message": "click needs a target selector"}
        try:
            await self.driver.page.click(action.target)
            return {"status": "ok", "action": "click", "target": action.target}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _type(self, action: Action) -> Dict[str, Any]:
        if not action.target or not action.text:
            return {"status": "error", "message": "type needs target and text"}
        try:
            await self.driver.page.fill(action.target, action.text)
            return {"status": "ok", "action": "type", "target": action.target}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _navigate(self, action: Action) -> Dict[str, Any]:
        if not action.target:
            return {"status": "error", "message": "navigate needs a URL"}
        try:
            await self.driver.goto(action.target)
            title = await self.driver.page.title()
            return {"status": "ok", "action": "navigate", "url": action.target, "title": title}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _scroll(self, action: Action) -> Dict[str, Any]:
        direction = action.direction or "down"
        amount = action.amount or 300
        try:
            sign = 1 if direction in ("down", "right") else -1
            await self.driver.page.evaluate(
                f"() => window.scrollBy(0, {sign * amount})"
            )
            return {"status": "ok", "action": "scroll", "direction": direction, "amount": amount}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _screenshot(self, action: Action) -> Dict[str, Any]:
        path = action.target or "screenshot.png"
        try:
            await self.driver.screenshot(path)
            return {"status": "ok", "action": "screenshot", "path": path}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _wait(self, action: Action) -> Dict[str, Any]:
        seconds = action.wait_seconds or 1.0
        await asyncio.sleep(seconds)
        return {"status": "ok", "action": "wait", "seconds": seconds}
