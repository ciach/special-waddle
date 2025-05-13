# JOI: Jira Observational Iterator

JOI (Jira Observational Iterator) is a toolkit for enhancing, decomposing, and generating tests for JIRA tickets using AI agents. It automates the review, structuring, and validation of ticket descriptions, helping teams ensure clarity, completeness, and readiness for development.

## What is JOI?

**JOI** stands for **Jira Observational Iterator**. It is designed to:
- Transform raw JIRA ticket descriptions into structured, actionable tickets.
- Apply multiple AI "agents" to review tickets from different perspectives (PM, Developer, QA, Security, Design).
- Decompose tickets into technical tasks.
- Generate automated test cases for requirements.
- Enforce input and output quality using "guardrails".

## File Overview

- `main.py`: The entry point for transforming and validating JIRA tickets. Runs the orchestration of all agents and applies guardrails to ensure ticket quality.
- `api_server.py`: Provides a FastAPI-based web API for programmatic access to JOI's main features (ticket enhancement, task breakdown, test generation).
- `task_manager.py`: Contains logic for breaking down enhanced JIRA tickets into smaller technical tasks. Can be used standalone or via the API.
- `test_generator.py`: Generates unit, integration, and end-to-end tests based on enhanced ticket Markdown files. Includes clarity checks and saves test output.
- `.env`: Stores environment variables (e.g., API keys, settings). **Do not overwrite without confirmation.**
- `pyproject.toml`: Python project dependencies and configuration.

## How to Use

### 1. Enhance a JIRA Ticket
Run the main script and follow the prompt:
```bash
python main.py
```
Paste your JIRA ticket description when prompted. The enhanced ticket will be saved as a Markdown file with agent comments and front matter.

### 2. Break Down Tasks
To decompose an enhanced ticket:
```bash
python task_manager.py
```
Provide the path to the enhanced Markdown ticket file. The script will append a task breakdown and save a new file.

### 3. Generate Tests
To generate tests from an enhanced ticket:
```bash
python test_generator.py
```
Provide the path to the enhanced Markdown ticket file. The script will generate and save test files in the `generated_tests/` directory.

### 4. Running Scripts Separately
Each script (`main.py`, `task_manager.py`, `test_generator.py`) can be run directly from the command line as shown above. Make sure your virtual environment is activated and your `.env` file is set up before running any script.

### 5. API Usage
Run the FastAPI server to access endpoints for automation:
```bash
uvicorn api_server:app --reload
```
- `/main` — Enhance a ticket (POST with `ticket_description`)
- `/task-manager` — Decompose tasks (POST with `markdown_content`)
- `/test-generator` — Generate tests (POST with `markdown_content`)

## Requirements
- Python 3.10+

### Setting up the Environment with uv
[uv](https://github.com/astral-sh/uv) is a fast Python package manager. To use it for this project:

1. Install uv (if not already):
   ```bash
   pip install uv
   ```
2. Create and activate a virtual environment:
   ```bash
   uv venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   uv pip install -r requirements.txt
   ```

Alternatively, you can use `python -m venv .venv` and `pip install -r requirements.txt` as usual.

### Environment Variables
- Copy `.env.SAMPLE` to `.env` and fill in your own values:
  ```bash
  cp .env.SAMPLE .env
  # Edit .env as needed
  ```
- **Never overwrite your `.env` file without confirming its contents.**

## Notes
- **Never overwrite your `.env` file without confirming its contents.**
- No mock or stub data is used outside of tests.
- All scripts are designed for clarity and modularity.

---

For more details, see the docstrings and comments in each file.
