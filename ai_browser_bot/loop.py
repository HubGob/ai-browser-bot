"""AI loop — snapshot, decide, act, repeat."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from ai_browser_bot.driver import BrowserDriver
from ai_browser_bot.dom import DOMInspector
from ai_browser_bot.actions import Action, ActionExecutor
from ai_browser_bot.llm import LLMClient
from ai_browser_bot.safety import SafetyPolicy
from ai_browser_bot.memory import SessionMemory


# ---------------------------------------------------------------------------
# Structured LLM output — we ask the LLM to emit a JSON object
# ---------------------------------------------------------------------------

class LLMResponse(BaseModel):
    """What we ask the LLM to return for each step."""

    action: Action
    reasoning: str = ""
    done: bool = False
    plan: Optional[List[str]] = None
    next_task: Optional[str] = None


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a browser automation assistant. You control a headless Chrome browser
via structured actions. Your job is to accomplish the user's task by observing
the page and issuing one action at a time.

Available actions:
- click:    {"type": "click", "target": "css_selector"}
- type:     {"type": "type", "target": "css_selector", "text": "text to type"}
- navigate: {"type": "navigate", "target": "https://url"}
- scroll:   {"type": "scroll", "direction": "up|down|left|right", "amount": 300}
- screenshot: {"type": "screenshot", "target": "path.png"}
- wait:     {"type": "wait", "wait_seconds": 1.0}

Rules:
1. Respond with a single JSON object matching the schema below.
2. Use the CSS selectors from the page snapshot to target elements.
3. After each action, you'll get a new snapshot — iterate.
4. Set "done": true when the task is complete.
5. If an action fails, try a different approach.
6. Keep reasoning concise — one sentence per step.
7. On the first step, include a "plan": ["step 1", "step 2", ...]
   listing the high-level sub-goals. On subsequent steps, update the
   plan to reflect progress and any new sub-goals.
"""


def build_user_prompt(
    task: str,
    snapshot: str,
    step: int,
    max_steps: int,
    last_result: Optional[Dict[str, Any]] = None,
    memory_summary: Optional[str] = None,
    current_plan: Optional[List[str]] = None,
) -> str:
    """Build the user-message prompt for one loop iteration."""
    lines = [
        f"### Task\n{task}\n",
        f"### Step {step} of {max_steps}\n",
    ]
    if current_plan:
        lines.append(f"### Current Plan\n" + "\n".join(f"  {i+1}. {p}" for i, p in enumerate(current_plan)) + "\n")
    if memory_summary:
        lines.append(f"### Memory\n{memory_summary}\n")
    lines.append(f"### Page Snapshot\n```\n{snapshot}\n```\n")
    if last_result:
        lines.append(f"### Last Action Result\n{last_result}\n")
    lines.append("### Your Response (JSON only)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


class AILoop:
    """Runs the snapshot → prompt → LLM → action cycle."""

    def __init__(
        self,
        driver: BrowserDriver,
        llm: LLMClient,
        task: str,
        max_steps: int = 20,
        dom_max_nodes: int = 200,
        safety: Optional[SafetyPolicy] = None,
        write_viewer_state: bool = False,
    ) -> None:
        self.driver = driver
        self.llm = llm
        self.task = task
        self.max_steps = max_steps
        self.inspector = DOMInspector(max_nodes=dom_max_nodes)
        self.executor = ActionExecutor(driver)
        self.safety = safety or SafetyPolicy()
        self.memory = SessionMemory()
        self.write_viewer_state = write_viewer_state
        self.action_log: List[str] = []

    def _write_viewer_state(self, step: int, status: str) -> None:
        """Write run_state.json + screenshot.png for the static viewer.

        The viewer polls run_state.json every second and renders the latest
        screenshot and action log from a scrolling list.
        """
        state = {
            "step": step,
            "status": status,
            "actions": self.action_log,
        }
        try:
            with open("run_state.json", "w") as f:
                json.dump(state, f, indent=2)
            # Screenshot path is fixed so the viewer img src stays stable
            # (cache-busting query param in viewer.html forces reload).
            screenshot_path = "screenshot.png"
            asyncio.create_task(
                self._try_screenshot(screenshot_path)
            )
        except Exception:
            # Viewer state is best-effort; never let it break the loop.
            pass

    async def _try_screenshot(self, path: str) -> None:
        try:
            await self.driver.screenshot(path)
        except Exception:
            pass

    async def run(self) -> Dict[str, Any]:
        """Run the loop until done or max_steps reached."""
        last_result: Optional[Dict[str, Any]] = None
        current_plan: Optional[List[str]] = None

        for step in range(1, self.max_steps + 1):
            snapshot, memory_summary = await self._collect(
                step, last_result, current_plan
            )

            prompt = build_user_prompt(
                self.task,
                snapshot,
                step,
                self.max_steps,
                last_result,
                memory_summary,
                current_plan,
            )

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            llm_result = await self.llm.chat(
                messages, response_format={"type": "json_object"}
            )

            if "error" in llm_result:
                self._log_action(
                    step, "error", f"LLM error: {llm_result['error']}"
                )
                result = {
                    "status": "error",
                    "step": step,
                    "error": llm_result["error"],
                }
                if self.write_viewer_state:
                    self._write_viewer_state(step, "error")
                return result

            # Parse the LLM's JSON response into our structured model
            try:
                parsed = LLMResponse.model_validate(
                    json.loads(llm_result["content"])
                )
            except Exception as e:
                self._log_action(step, "parse_error", str(e))
                result = {"status": "parse_error", "step": step, "error": str(e)}
                if self.write_viewer_state:
                    self._write_viewer_state(step, "parse_error")
                return result

            # Update plan if provided
            if parsed.plan is not None:
                current_plan = parsed.plan

            # Safety check before executing
            action_dict = parsed.action.model_dump()
            safety_violation = self.safety.check(action_dict)
            if safety_violation:
                error_result = {"status": "error", "message": safety_violation}
                self.memory.record(step, action_dict, error_result, snapshot)
                last_result = error_result
                self._log_action(step, action_dict["type"], "blocked")
                if self.write_viewer_state:
                    self._write_viewer_state(step, "error")
                continue

            # Execute
            last_result = await self.executor.execute(parsed.action)
            self.memory.record(step, action_dict, last_result, snapshot)
            self._log_action(
                step, action_dict["type"], last_result.get("status", "?")
            )

            if self.write_viewer_state:
                self._write_viewer_state(step, "running")

            if parsed.done:
                result = {
                    "status": "done",
                    "step": step,
                    "reasoning": parsed.reasoning,
                    "plan": current_plan,
                    "last_result": last_result,
                }
                if self.write_viewer_state:
                    self._write_viewer_state(step, "done")
                return result

        result = {
            "status": "max_steps_reached",
            "step": self.max_steps,
            "plan": current_plan,
            "last_result": last_result,
        }
        if self.write_viewer_state:
            self._write_viewer_state(self.max_steps, "max_steps_reached")
        return result

    async def _collect(
        self,
        step: int,
        last_result: Optional[Dict[str, Any]],
        current_plan: Optional[List[str]],
    ) -> tuple[str, Optional[str]]:
        snapshot = await self.inspector.snapshot(self.driver.page)
        memory_summary = self.memory.summary() if step > 1 else None
        return snapshot, memory_summary

    def _log_action(self, step: int, action_type: str, outcome: str) -> None:
        entry = f"Step {step}: {action_type} -> {outcome}"
        self.action_log.append(entry)
        # Keep the log bounded for memory safety
        if len(self.action_log) > 100:
            self.action_log = self.action_log[-100:]
