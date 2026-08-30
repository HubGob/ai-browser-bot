"""Simple session memory for the AI loop."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class SessionMemory:
    """Stores a rolling window of step observations."""

    def __init__(self, max_entries: int = 10) -> None:
        self.max_entries = max_entries
        self._entries: List[Dict[str, Any]] = []

    def record(
        self,
        step: int,
        action: Dict[str, Any],
        result: Dict[str, Any],
        snapshot_preview: Optional[str] = None,
    ) -> None:
        entry = {
            "step": step,
            "action": action,
            "result": result,
        }
        if snapshot_preview:
            entry["snapshot_preview"] = snapshot_preview[:200]
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            self._entries.pop(0)

    def recent(self, n: int = 3) -> List[Dict[str, Any]]:
        """Return the most recent n entries."""
        return self._entries[-n:]

    def summary(self) -> str:
        """Return a compact text summary of recent steps."""
        if not self._entries:
            return "No steps taken yet."
        lines = ["Recent steps:"]
        for e in self.recent(5):
            lines.append(
                f"  Step {e['step']}: {e['action']['type']} "
                f"→ {e['result'].get('status', '?')}"
            )
        return "\n".join(lines)

    def clear(self) -> None:
        self._entries.clear()
