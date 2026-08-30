"""Tests for SessionMemory."""

import pytest
from ai_browser_bot.memory import SessionMemory


def test_record_and_recent():
    mem = SessionMemory(max_entries=5)
    mem.record(1, {"type": "navigate"}, {"status": "ok"})
    mem.record(2, {"type": "click"}, {"status": "ok"})
    recent = mem.recent(2)
    assert len(recent) == 2
    assert recent[0]["step"] == 1
    assert recent[1]["step"] == 2


def test_max_entries_evicts_old():
    mem = SessionMemory(max_entries=3)
    for i in range(5):
        mem.record(i, {"type": "wait"}, {"status": "ok"})
    assert len(mem._entries) == 3
    assert mem._entries[0]["step"] == 2  # evicted steps 0,1


def test_summary():
    mem = SessionMemory()
    mem.record(1, {"type": "navigate"}, {"status": "ok"})
    mem.record(2, {"type": "click"}, {"status": "error"})
    summary = mem.summary()
    assert "Step 1" in summary
    assert "Step 2" in summary
    assert "ok" in summary
    assert "error" in summary


def test_clear():
    mem = SessionMemory()
    mem.record(1, {"type": "navigate"}, {"status": "ok"})
    mem.clear()
    assert mem.recent(10) == []
    assert mem.summary() == "No steps taken yet."
