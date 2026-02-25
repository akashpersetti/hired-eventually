# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies:**
```bash
uv sync
```

**Run the app:**
```bash
uv run python app.py
```

Or using Gradio directly:
```bash
uv run gradio app.py
```

**Run the notebook (for prototyping/testing):**
```bash
uv run jupyter notebook try.ipynb
```

## Architecture

This is a two-file application:

- **`cover_letter.py`** — Core async logic. Uses a two-phase pipeline:
  1. **cv-forge phase**: Spawns `npx cv-forge` as an MCP server via `MCPServerStdio` (from `openai-agents`), calls `parse_job_requirements` then `generate_cover_letter` to get structured job requirements and a draft cover letter.
  2. **LLM polish phase**: Sends the raw resume text, job description, cv-forge requirements, and draft to the selected LLM provider to produce the final JSON `{"cover_letter": "...", "company_name": "..."}`.

  Returns a Pydantic `CoverLetter` model with `cover_letter` (text) and `company_name` fields. `_parse_cover_letter_json` handles fallback if the LLM doesn't return valid JSON.

- **`app.py`** — Gradio UI layer. Implements progressive disclosure (each input field reveals the next only after the previous is filled). Calls `generate_cover_letter` from `cover_letter.py`. Handles download (temp `<company>_<mmdd>.txt` file) and clipboard copy via JS.

**Supported models and routing** (`cover_letter.py:284`):
| UI dropdown value | Provider | Required env var |
|---|---|---|
| `gpt-5.2` | OpenAI (`openai` client) | `OPENAI_API_KEY` |
| `claude-sonnet-4-0` | Anthropic (`anthropic` client) | `ANTHROPIC_API_KEY` |
| `gemini-3-flash-preview` | Google (via OpenAI-compatible endpoint) | `GOOGLE_API_KEY` |

**MCP dependency:** Node.js/npm must be available in `PATH` because `_run_cv_forge` spawns `npx cv-forge` as a subprocess MCP server.

**Environment:** Requires a `.env` file (loaded via `python-dotenv`). Set whichever API keys correspond to the models you intend to use.

**Hardcoded personal info:** `_build_basic_user_profile` in `cover_letter.py:42` has hardcoded personal details (name, email). Update these if deploying for a different user.

**Prototyping:** `try.ipynb` reflects the same pipeline logic as `cover_letter.py` and is useful for quick iteration.
