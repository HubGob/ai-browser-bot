"""Safety guardrails for the AI browser bot."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Set
from urllib.parse import urlparse


class SafetyPolicy:
    """Configurable safety rules for AI-driven browser actions."""

    def __init__(
        self,
        allowed_domains: Optional[Set[str]] = None,
        max_scroll_amount: int = 2000,
        max_wait_seconds: float = 10.0,
    ) -> None:
        self.allowed_domains = allowed_domains or set()
        self.max_scroll_amount = max_scroll_amount
        self.max_wait_seconds = max_wait_seconds

    def check(self, action: Dict[str, Any]) -> Optional[str]:
        """Return an error string if the action is unsafe, or None if OK."""
        atype = action.get("type")

        # javascript: URIs are always blocked
        if atype == "navigate":
            url = action.get("target", "")
            if url.startswith("javascript:"):
                return f"Navigation blocked: javascript: URIs are not allowed"
            if self.allowed_domains:
                host = urlparse(url).hostname or ""
                if host not in self.allowed_domains:
                    return f"Navigation blocked: {host} not in allowed domains"

        if atype in ("click", "type"):
            selector = action.get("target", "")
            if self._is_dangerous_selector(selector):
                return f"Blocked dangerous selector: {selector}"

        if atype == "scroll":
            amount = action.get("amount", 0)
            if amount > self.max_scroll_amount:
                return f"Scroll amount {amount} exceeds max {self.max_scroll_amount}"

        if atype == "wait":
            seconds = action.get("wait_seconds", 0)
            if seconds > self.max_wait_seconds:
                return f"Wait {seconds}s exceeds max {self.max_wait_seconds}s"

        return None

    def _is_dangerous_selector(self, selector: str) -> bool:
        if not selector:
            return False
        dangerous = [
            re.compile(r"^.*<script.*$"),   # contains script tags
            re.compile(r"^javascript:"),    # JS URIs
            re.compile(r"<.*>"),             # raw HTML injection attempts
        ]
        for pat in dangerous:
            if pat.match(selector):
                return True
        return False
