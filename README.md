# AI Browser Bot — From Scratch

Browser automation agent built from the ground up in Python + Playwright + LLM. Not a wrapper — real implementation for the systems/backend engineering path.

## What it does

You give it a task in plain English (or Tagalog, kung gusto mo) and it:

1. Launches a headless Chrome via Playwright
2. Takes a compact DOM snapshot
3. Sends it to an LLM with your instruction
4. Parses the LLM response into a browser action
5. Executes the action
6. Repeats until done or step budget exhausted

## Architecture

```
┌─────────────────────────────┐
│  AI Loop                     │
│  - planning                  │
│  - memory                    │
│  - safety policy             │
└─────────────┬───────────────┘
              │
┌─────────────▼───────────────┐
│  Action Executor             │
│  - click, type, navigate     │
│  - scroll, wait              │
└─────────────┬───────────────┘
              │
┌─────────────▼───────────────┐
│  DOM Inspector               │
│  - filtered snapshot         │
│  - LLM-friendly format       │
└─────────────┬───────────────┘
              │
┌─────────────▼───────────────┐
│  Playwright Driver           │
│  - launch, navigate          │
│  - screenshot, close         │
└─────────────────────────────┘
```

Each layer is an independent Python module. May tests lahat.

## Tech stack

- Python 3.11+
- [Playwright](https://playwright.dev/python/) — async browser control
- [Pydantic](https://docs.pydantic.dev/) — structured output parsing
- [pytest](https://docs.pytest.org/) + [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) — testing
- OpenAI-compatible LLM (OpenAI, Azure, LM Studio, etc.)

## Setup

```bash
cd ai_browser_bot
pip install -e ".[dev]"
playwright install chromium
```

Kailangan ng `OPENAI_API_KEY` para sa real usage. Para sa demo/test, may mock na.

## Run

```bash
# Demo mode (no API key needed)
python -m ai_browser_bot.demo

# CLI mode (needs API key)
OPENAI_API_KEY=sk-... python -m ai_browser_bot.cli "go to example.com and tell me the title"
```

## Test

```bash
pytest tests/ -v
```

May 8 test files na — test_actions, test_cli, test_dom, test_driver, test_llm, test_loop, test_memory, test_safety.

## How the loop works

1. **AI Loop** (`loop.py`) — manages the planning cycle. Each iteration: get DOM snapshot → send to LLM → parse response → execute action → check if done.
2. **Safety** (`safety.py`) — policy layer. Prevents dangerous actions (e.g., visiting suspicious URLs, clicking without confirmation). Kasi hindi naman pwedeng mag-isa lang ang AI, may guardrails dapat.
3. **Memory** (`memory.py`) — session-level memory. Tracks what happened across steps. Para hindi malilimtan kung ano ang nangyari.
4. **Actions** (`actions.py`) — defines the action space (click, type, navigate, scroll, wait, screenshot, etc.). Each action is a Pydantic model na pinaparse from LLM output.
5. **LLM** (`llm.py`) — OpenAI-compatible client. Pluggable — pwede i-switch ang provider.
6. **DOM** (`dom.py`) — inspects the page and produces a compact text snapshot. Skips script/style tags, limits text length.
7. **Driver** (`driver.py`) — low-level Playwright wrapper. Launches browser, navigates, takes screenshots.

## Status

WIP — construction phase pa lang. Working on the core loop integration.

## Photos/screenshots

Wala pa — once stable, ididagdag ko yung screenshots ng bot in action. For now, here's the ASCII diagram sa itaas.

## License

MIT
