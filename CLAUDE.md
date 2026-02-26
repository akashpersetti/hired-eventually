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

**Run the notebook (for prototyping/testing):**
```bash
uv run jupyter notebook try.ipynb
```

## Architecture

This is a two-file application:

- **`cover_letter.py`** — Core async logic. Uses a two-phase pipeline:
  1. **cv-forge phase**: Spawns `npx cv-forge` as an MCP server via `MCPServerStdio` (from `openai-agents`), calls `parse_job_requirements` then `generate_cover_letter` to get structured job requirements and a draft cover letter.
  2. **LLM polish phase**: Sends the resume text, job description, cv-forge requirements, and draft to the selected LLM provider. The LLM returns JSON which is parsed into a `CoverLetter` Pydantic model. `_parse_cover_letter_json` handles fallback if the LLM doesn't return valid JSON.

- **`app.py`** — Gradio UI layer. Implements progressive disclosure (each input reveals the next only after the previous is filled). After a successful generation, fires `log_application_to_xlsx` as an `asyncio.create_task` (background, non-blocking). Handles download (temp `<company>_<mmdd>.txt`) and clipboard copy via JS.

**`CoverLetter` model fields:**
| Field | Type | Description |
|---|---|---|
| `cover_letter` | `str` | The full cover letter text |
| `company_name` | `str` | Company name extracted from the JD |
| `role_applied` | `str` | Job title/role from the JD |
| `job_id` | `str \| None` | Job ID if explicitly stated in the JD |

**Supported models and routing** (`cover_letter.py`, `generate_cover_letter` function):
| UI dropdown value | Provider | Required env var |
|---|---|---|
| `gpt-5.2` | OpenAI (`openai` client) | `OPENAI_API_KEY` |
| `claude-sonnet-4-0` | Anthropic (`anthropic` client) | `ANTHROPIC_API_KEY` |
| `gemini-3-flash-preview` | Google (via OpenAI-compatible endpoint) | `GOOGLE_API_KEY` |

**`log_application_to_xlsx`**: Appends a new row to `job_apps.xlsx` after each generation. Uses `openpyxl` directly — scans column A to find the last sheet row with a positive integer, writes the new row immediately after it, and copies cell styles (font, fill, border, alignment, number format, row height) from the previous row to match formatting.

**`job_apps.xlsx` structure:** Row 1 = column headers (`#`, Company, Role, Job ID, Link, Accepted/Rejected). Data rows start at row 2, with column A holding the sequential row number. Column F (Accepted/Rejected) is never written by the app.

**MCP dependency:** Node.js/npm must be available in `PATH` because `_run_cv_forge` spawns `npx cv-forge` as a subprocess MCP server.

**Environment:** Requires a `.env` file (loaded via `python-dotenv`). Set whichever API keys correspond to the models you intend to use.

**Hardcoded personal info:** `_build_basic_user_profile` in `cover_letter.py` has hardcoded name and email. Update these if deploying for a different user.

**Prototyping:** `try.ipynb` mirrors the same pipeline and is useful for quick iteration outside the UI.
