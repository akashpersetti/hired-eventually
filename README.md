# Hired (Eventually)

A local, AI-powered job application assistant. Generate tailored cover letters from your resume and a job description, automatically log every application to an Excel tracker, and mark outcomes - all from a clean web UI.

---

## Features

- **Cover letter generation** — uses a two-phase pipeline: a structured draft from [cv-forge](https://www.npmjs.com/package/cv-forge) (via MCP), then a polished final version from your chosen LLM.
- **Multi-model support** — switch between Claude (Anthropic), GPT (OpenAI), and Gemini (Google) from a dropdown.
- **Auto-logging** — every generated cover letter is automatically appended to a local `job_apps.xlsx` tracker with company, role, job ID, and application link.
- **Application tracker** — view your full application history in a table with clickable job links.
- **Status tracking** — mark applications as Accepted or Rejected directly from the UI.
- **Auth-protected** — basic username/password login via environment variables.
- **PWA-ready** — installable as a desktop app from the browser.

---

## Prerequisites

Before installing, make sure you have the following:

### 1. Python 3.12+

```bash
python --version   # should be 3.12 or higher
```

### 2. [uv](https://docs.astral.sh/uv/) (package manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Node.js and npm

Required to run the `cv-forge` MCP server, which is invoked internally via `npx`.

```bash
node --version    # v18+ recommended
npm --version
```

Install Node.js from [nodejs.org](https://nodejs.org) if not present.

### 4. API Keys

You need at least one of the following depending on which model you want to use:

| Model (UI dropdown) | Provider | Environment variable |
|---|---|---|
| `claude-sonnet-4-0` | Anthropic | `ANTHROPIC_API_KEY` |
| `gpt-5.2` | OpenAI | `OPENAI_API_KEY` |
| `gemini-3-flash-preview` | Google | `GOOGLE_API_KEY` |

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/akashpersetti/hired-eventually.git
cd hired-eventually
```

### 2. Install Python dependencies

```bash
uv sync
```

This creates a `.venv` directory and installs all dependencies from `pyproject.toml`.

### 3. Set up environment variables

Create a `.env` file in the project root:

```bash
cp .env.example .env   # if an example exists, otherwise create manually
```

> **Note:** The `.env` file is listed in `.gitignore` and will never be committed.

### 4. Set up the Excel tracker

Create a file named `job_apps.xlsx` in the project root. The app expects a specific sheet structure:

**Sheet name:** `Sheet 1` (exactly, including the space)

**Row 1 — Column headers** (in this exact order):

| A | B | C | D | E | F |
|---|---|---|---|---|---|
| `#` | `Company` | `Role` | `Job ID` | `Link` | `Accepted/Rejected` |

**Row 2 onwards** — data rows, written automatically by the app. Leave these empty initially.

> **Important:** The sheet name must be `Sheet 1`. The header row must be row 1. Do not add a title row above the headers. The app scans column A for the last positive integer to determine where to append the next entry — any deviation from this structure will cause incorrect row placement.

To create the file quickly:

1. Open Excel or Google Sheets
2. Rename the sheet tab to `Sheet 1`
3. In row 1, type the headers exactly as shown above
4. Save as `.xlsx`

> `job_apps.xlsx` is listed in `.gitignore` and will never be committed to git (it contains personal job application data).

---

## Quickstart

```bash
uv run app.py
```

Then open [http://localhost:7860](http://localhost:7860) in your browser. Log in with the `APP_USERNAME` and `APP_PASSWORD` you set in `.env`.

> **First run:** `npx cv-forge` will be downloaded and cached by npm automatically on first use. This adds a few seconds to the first generation.

---

## Usage Guide

### Tab 1 — Generate Cover Letter

The form uses **progressive disclosure** — each field appears only after the previous one is filled.

1. **Upload resume (PDF)** — upload your resume. Accepted format: `.pdf` only.
2. **Job description** — appears after resume upload. Paste the full job description text.
3. **Model** — appears after job description is filled. Select your preferred LLM.
4. **Application link** — paste the URL of the job posting (optional but recommended for tracking).
5. **Generate** — click to generate. The app will:
   - Call `cv-forge` (via MCP over stdio) to parse job requirements and produce a draft.
   - Send the draft, resume text, and job description to the selected LLM for a polished final letter.
   - Display the result with **copy to clipboard** (📋) and **download as `.txt`** (📥) buttons.
   - Automatically append a new row to `job_apps.xlsx` in the background.

**Download filename format:** `<CompanyName>_<MMDD>.txt` (e.g., `Google_0226.txt`)

---

### Tab 2 — Applications

Displays your full application history loaded from `job_apps.xlsx`.

- Click **↻** to reload the table from disk.
- The **Link** column renders as a clickable **↗** hyperlink.
- The table is read-only.

---

### Tab 3 — Mark Accepted / Rejected

1. Select the application from the dropdown (format: `#. Company — Role`).
2. Click **Accepted** or **Rejected** — the status column in `job_apps.xlsx` is updated immediately with ✅ or ❌.
3. The table below refreshes automatically to reflect the change.
4. Click **↻** to manually refresh both the table and the dropdown.

---

## Configuration Reference

### `.env` variables

| Variable | Required | Description |
|---|---|---|
| `APP_USERNAME` | Yes | Login username for the web UI |
| `APP_PASSWORD` | Yes | Login password for the web UI |
| `ANTHROPIC_API_KEY` | If using Claude | Anthropic API key |
| `OPENAI_API_KEY` | If using GPT | OpenAI API key |
| `GOOGLE_API_KEY` | If using Gemini | Google AI API key |
| `FULL_NAME` | Yes | For building user profile |
| `EMAIL` | Yes | For building user profile |

### `job_apps.xlsx` column reference

| Column | Header | Written by | Notes |
|---|---|---|---|
| A | `#` | App (auto-incremented) | Sequential integer starting at 1 |
| B | `Company` | App (from LLM response) | Extracted from job description |
| C | `Role` | App (from LLM response) | Job title extracted from job description |
| D | `Job ID` | App (from LLM response) | Null if not stated in job description |
| E | `Link` | App (from UI input) | The application link you paste in the UI |
| F | `Accepted/Rejected` | App (via Mark tab) | ✅ for Accepted, ❌ for Rejected |

---

## Project Structure

```
.
├── app.py              # Gradio UI — all tabs, event handlers, CSS
├── cover_letter.py     # Core logic — LLM calls, xlsx read/write, cv-forge MCP
├── try.ipynb           # Prototyping notebook (mirrors cover_letter.py pipeline)
├── job_apps.xlsx       # Job application tracker (gitignored)
├── .env                # API keys and credentials (gitignored)
├── pyproject.toml      # Project dependencies (managed by uv)
```

---

## How the Generation Pipeline Works

Each cover letter generation runs a two-phase pipeline:

**Phase 1 — cv-forge (MCP)**
The app spawns `npx cv-forge` as a local MCP server over stdio. It calls two tools:
- `parse_job_requirements` — extracts structured requirements (job title, company, required skills) from the raw job description.
- `generate_cover_letter` — produces an initial draft cover letter using a built-in profile + the parsed requirements.

**Phase 2 — LLM polish**
The selected LLM receives:
- Your raw resume text (extracted from the uploaded PDF)
- The raw job description
- The structured requirements from Phase 1
- The draft cover letter from Phase 1

It returns a JSON object with `cover_letter`, `company_name`, `role_applied`, and `job_id`. The cover letter is displayed and the metadata is used for logging.

---

## Running as a PWA (Optional)

To install the app as a desktop app via the browser:

```python
# In app.py, add pwa=True to launch()
app.launch(
    auth=(...),
    theme=...,
    css=...,
    head=...,
    pwa=True,
)
```

After restarting, an install icon will appear in your browser's address bar.

---

## Troubleshooting

**`npx: command not found`**
Node.js is not installed or not in your PATH. Install from [nodejs.org](https://nodejs.org).

**`cv-forge` takes a long time on first run**
npm is downloading and caching the package. Subsequent runs are fast.

**New row added with wrong formatting in Excel**
The app copies cell styles from the previous data row. If the first data row (row 2) has no formatting, subsequent rows will also be plain. This is expected and harmless.

**`GOOGLE_API_KEY is not set`**
You selected Gemini but haven't added `GOOGLE_API_KEY` to your `.env` file.

**Sheet not found / wrong sheet name**
Make sure the sheet tab in `job_apps.xlsx` is named exactly `Sheet 1` (capital S, space, number 1).

---

## Deploying to Hugging Face Spaces

> ⚠️ This app is designed and tested for **local use**. Deploying to HF Spaces requires several non-trivial changes. The notes below outline what needs to be addressed.

### 1. README frontmatter

HF Spaces requires a YAML metadata block at the very top of `README.md`. **Remove all existing content from the top of this file** and replace it with:

```yaml
---
title: Hired (Eventually)
emoji: 📄
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: "6.6.0"
app_file: app.py
pinned: false
---
```

Then add the rest of the README content below it.

### 2. Node.js / npx availability

`cv-forge` is invoked via `npx` at runtime. HF Spaces (Docker-based) does not include Node.js by default. You need to add a `packages.txt` file to the repo root:

```
nodejs
npm
```

HF Spaces will install these system packages before starting the app.

### 3. Ephemeral filesystem

HF Spaces resets the filesystem on every restart. This means `job_apps.xlsx` **will be wiped** on each redeploy or restart — all your logged applications will be lost. Options to work around this:
- Use [HF Datasets](https://huggingface.co/docs/datasets) as a persistent storage backend instead of a local `.xlsx` file.
- Use an external database or cloud storage (S3, Google Sheets API, etc.).

### 4. Environment variables / secrets

Do not upload a `.env` file. Instead, set all environment variables as **Secrets** in your Space settings (Settings → Variables and Secrets). The app reads them via `os.getenv()` so no code changes are needed.

### 5. `app.launch()` — remove auth or keep it

HF Spaces has its own access control (public/private Space). If you make the Space private, you can remove `auth=` from `app.launch()`. If you keep it public and still want a login gate, keep `auth=` and set `APP_USERNAME`/`APP_PASSWORD` as secrets.

### 6. Dependencies

HF Spaces can use `requirements.txt` or `pyproject.toml`. Since this project uses `pyproject.toml` with `uv`, add a `requirements.txt` generated from it, or configure the Space to use `uv` as the package manager.
