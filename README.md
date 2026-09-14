# AI Browser Bot

[![CI](https://github.com/HubGob/ai-browser-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/HubGob/ai-browser-bot/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/ai-browser-bot.svg)](https://pypi.org/project/ai-browser-bot/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Browser automation built from scratch in Python + Playwright + an LLM. You give
it a natural-language task and it drives a real browser — snapshot the DOM, ask
the LLM what to do, execute the action, repeat. Not a wrapper: the decision loop
and safety policy are hand-written.

---

## 🚀 60-second quickstart

```bash
# 1. Install (Python 3.11+)
pip install -e ".[dev]"

# 2. Install browser binaries (one-time)
playwright install chromium

# 3. Set your key (OpenAI) — or leave unset for local servers
export OPENAI_API_KEY=sk-your-key-here

# 4. Run it
ai-bot "go to example.com and tell me the title"
```

Want to try it first without a key? Run the built-in mock demo:

```bash
python -m ai_browser_bot.demo
```

### Watching the bot live

```bash
ai-bot --viewer "search the web for today's weather"
```

This writes `run_state.json` and `screenshot.png` to the current directory each
step. Open **`viewer.html`** in any browser (no server needed) to see a live,
auto-refreshing feed of the screenshot and action log.

---

## How it decides actions

Each iteration of the loop:

1. **Snapshot** — `DOMInspector` walks the page and emits a compact, LLM-friendly
   text representation of interactive elements (buttons, links, inputs) plus
   visible text. Script/style/SVG content is stripped.
2. **Prompt** — the snapshot, the task, the current plan, and a rolling memory
   summary are assembled into a single user message. A fixed system prompt
   constrains the LLM to emit **one JSON object** matching the `LLMResponse`
   schema (an `Action` + optional `reasoning`, `plan`, and `done` flag).
3. **Decide** — the JSON is parsed and validated with Pydantic into an `Action`.
4. **Check** — `SafetyPolicy.check()` reviews the action *before* it touches the
   page.
5. **Act** — the approved action is dispatched via `ActionExecutor`, which maps
   it to a Playwright call (click, type, navigate, scroll, wait, screenshot).

The cycle repeats until `done` is `true`, the step budget (`--max-steps`) is
exhausted, or an unrecoverable error occurs.

### Action space

| Action     | Fields                          | Effect                     |
| ---------- | ------------------------------- | -------------------------- |
| `click`    | `target` (CSS selector)         | Click an element           |
| `type`     | `target`, `text`                | Fill an input              |
| `navigate` | `target` (URL)                  | Go to a page               |
| `scroll`   | `direction`, `amount` (px)      | Scroll the page            |
| `screenshot` | `target` (path)               | Save a PNG                 |
| `wait`     | `wait_seconds`                  | Pause                        |

---

## Safety policy

`SafetyPolicy` is the guardrail layer. Every action is validated **before**
execution, and any violation short-circuits the step with an error result
rather than touching the browser.

By default it enforces:

- **`javascript:` URIs are always blocked.** A `navigate` action whose `target`
  starts with `javascript:` is rejected — this prevents script injection via
  navigation.
- **Domain allowlisting.** When `allowed_domains` is configured, any `navigate`
  target whose host is not in the allowlist is blocked. (Empty = allow all,
  which is the default.)
- **Dangerous click/type selectors.** Selectors matching `<script…>` patterns,
  `javascript:` URIs, or raw HTML injection (`<img … onerror=…>`) are refused.
- **Bounded scroll.** A `scroll` action whose `amount` exceeds `max_scroll_amount`
  (default 2000px) is rejected.
- **Bounded wait.** A `wait` action whose `wait_seconds` exceeds
  `max_wait_seconds` (default 10s) is rejected.

The key is resolved from `--api-key`, then the `OPENAI_API_KEY` or `LLM_API_KEY`
environment variable. For self-hosted / local providers that don't need a key,
use `--llm-url` to point elsewhere.

---

## Provider examples

The LLM client speaks any **OpenAI-compatible** HTTP API. Pick your backend via
`--llm-url` (or `OPENAI_BASE_URL` in `.env`).

### OpenAI (hosted)

```bash
export OPENAI_API_KEY=sk-…
ai-bot --llm-model gpt-4o "go to example.com and tell me the title"
```

### Any Anthropic-compatible proxy

Point at an OpenAI-compatible proxy (e.g. one that translates to Anthropic's
format) and pass the appropriate key:

```bash
ai-bot \
  --llm-url https://api.anthropic-compatible.example/v1 \
  --api-key $PROXY_KEY \
  "summarise the first paragraph on example.com"
```

### Local models (Ollama / LM Studio)

No key required — run locally and point the client at the OpenAI-compatible
endpoint:

```bash
# Ollama, serving llama3 via its OpenAI-compatible API on :11434
ai-bot --llm-url http://localhost:11434/v1 --llm-model llama3 \
  --api-key ollama "what is the title of example.com"

# LM Studio (listens on 1234 by default)
ai-bot --llm-url http://localhost:1234/v1 --llm-model Llama-3-8B-Instruct \
  --api-key lmstudio "open example.com"
```

### Configuration via `.env`

Copy the example and edit:

```bash
cp .env.example .env
# then set OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL, etc.
```

The CLI calls `load_dotenv()` on startup, so your `.env` is picked up
automatically. Keys are resolved in this order: `--api-key` flag →
`OPENAI_API_KEY` env → `LLM_API_KEY` env.

---

## Demo

<!-- TODO: replace this placeholder with a short GIF/screen-capture of the
     bot in action (e.g. `asciinema` cast or a recorded `screenshot.png`
     sequence). Keep it under 30s. -->
![Demo GIF placeholder — a recording of the bot driving a browser will go here]
(https://via.placeholder.com/800x450?text=Demo+GIF+coming+soon)

---

## Installation

Published as [`ai-browser-bot`](https://pypi.org/project/ai-browser-bot/) on
PyPI and mirrored to **TestPyPI**:

```bash
# Stable (when published)
pip install ai-browser-bot

# Prerelease / bleeding edge from TestPyPI
pip install --pre -i https://test.pypi.org/simple/ ai-browser-bot
```

To install from source (recommended for development):

```bash
git clone https://github.com/HubGob/ai-browser-bot.git
cd ai-browser-bot
pip install -e ".[dev]"
playwright install chromium
```

---

## Testing

```bash
pytest tests/ -v
```

The suite covers the action executor, DOM inspector, driver lifecycle, LLM
client, AI loop, session memory, safety policy, and CLI parsing — including
explicit failure-path tests for malformed LLM output, blocked actions, and the
missing-key CLI exit path.

## License

MIT — see [`LICENSE`](LICENSE).
