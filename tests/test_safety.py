"""Tests for SafetyPolicy."""

import pytest
from ai_browser_bot.safety import SafetyPolicy


def test_navigate_to_allowed_domain():
    policy = SafetyPolicy(allowed_domains={"example.com"})
    action = {"type": "navigate", "target": "https://example.com/page"}
    assert policy.check(action) is None


def test_navigate_to_blocked_domain():
    policy = SafetyPolicy(allowed_domains={"example.com"})
    action = {"type": "navigate", "target": "https://evil.com"}
    err = policy.check(action)
    assert err is not None
    assert "evil.com" in err


def test_click_safe_selector():
    policy = SafetyPolicy()
    action = {"type": "click", "target": "#submit-btn"}
    assert policy.check(action) is None


def test_javascript_uri_blocked():
    policy = SafetyPolicy()
    action = {"type": "navigate", "target": "javascript:alert(1)"}
    err = policy.check(action)
    assert err is not None


def test_scroll_amount_limit():
    policy = SafetyPolicy(max_scroll_amount=500)
    action = {"type": "scroll", "direction": "down", "amount": 1000}
    err = policy.check(action)
    assert err is not None
    assert "exceeds max" in err


def test_wait_limit():
    policy = SafetyPolicy(max_wait_seconds=5.0)
    action = {"type": "wait", "wait_seconds": 20.0}
    err = policy.check(action)
    assert err is not None


def test_no_restrictions_means_all_allowed():
    policy = SafetyPolicy()  # no domain allowlist, defaults for scroll/wait
    for action in [
        {"type": "navigate", "target": "https://any.com"},
        {"type": "click", "target": "div"},
        {"type": "scroll", "direction": "down", "amount": 500},   # within default 2000
        {"type": "wait", "wait_seconds": 3},                      # within default 10
    ]:
        assert policy.check(action) is None


def test_raw_html_injection_blocked():
    policy = SafetyPolicy()
    action = {"type": "click", "target": "<img src=x onerror=alert(1)>"}
    err = policy.check(action)
    assert err is not None
