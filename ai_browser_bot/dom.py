"""DOM inspection — produces LLM-friendly page snapshots."""

from __future__ import annotations

from typing import List, Optional

from playwright.async_api import ElementHandle, Page

# Tags we skip when building a snapshot
SKIP_TAGS: set[str] = {
    "script", "style", "noscript", "template", "svg", "path", "circle",
}

# Attributes whose values we include (others are dropped)
KEEP_ATTRIBS: set[str] = {"id", "name", "type", "placeholder", "aria-label"}


class DOMInspector:
    """Extracts a compact text snapshot of a Playwright page's DOM.

    The snapshot is designed to be small enough for an LLM context window
    while preserving interactive elements (buttons, inputs, links) and
    visible text.
    """

    def __init__(self, max_nodes: int = 200, include_attributes: bool = True) -> None:
        self.max_nodes = max_nodes
        self.include_attributes = include_attributes

    async def snapshot(self, page: Page) -> str:
        """Return a text snapshot of the page's interactive DOM."""
        elements = await self._collect_interactive_elements(page)
        lines: list[str] = []
        for el in elements[: self.max_nodes]:
            line = self._format_element(el)
            if line:
                lines.append(line)
        return "\n".join(lines)

    async def _collect_interactive_elements(self, page: Page) -> list[dict]:
        """Collect clickable, input, and text-bearing elements."""
        results: list[dict] = []

        # Clickable elements
        clickable = await page.query_selector_all(
            "button, a, [onclick], input[type=button], input[type=submit], "
            "input[type=reset], details, summary"
        )
        for el in clickable:
            info = await self._element_info(el)
            if info:
                results.append(info)

        # Input elements
        inputs = await page.query_selector_all(
            "input:not([type=hidden]), textarea, select"
        )
        for el in inputs:
            info = await self._element_info(el)
            if info:
                results.append(info)

        # Text paragraphs (limited — only those with substantial text)
        paragraphs = await page.query_selector_all(
            "p, h1, h2, h3, h4, h5, h6, li, span, div"
        )
        for el in paragraphs:
            info = await self._element_info(el, max_text_len=300)
            if info and len(info["text"]) > 10:
                results.append(info)

        return results

    async def _element_info(
        self, el: ElementHandle, max_text_len: int = 200
    ) -> Optional[dict]:
        tag = await el.evaluate("el => el.tagName.toLowerCase()")
        if tag in SKIP_TAGS:
            return None

        text = (await el.inner_text()).strip()
        if not text and tag not in ("input", "textarea", "select", "button", "a"):
            return None

        if len(text) > max_text_len:
            text = text[:max_text_len] + "…"

        attribs: dict = {}
        if self.include_attributes:
            for attr in KEEP_ATTRIBS:
                val = await el.get_attribute(attr)
                if val:
                    attribs[attr] = val

        return {
            "tag": tag,
            "text": text,
            "attribs": attribs,
        }

    def _format_element(self, info: dict) -> str:
        tag = info["tag"]
        # Collapse whitespace (including newlines) so one element = one line
        text = " ".join(info["text"][:120].split())
        parts = [f"<{tag}>"]

        if info["attribs"]:
            for k, v in info["attribs"].items():
                parts.append(f'{k}="{v}"')

        if text:
            parts.append(f'text="{text}"')

        return " ".join(parts)
