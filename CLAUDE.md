# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Spendly** — a Flask + SQLite expense tracker built as a step-by-step learning project (CampusX playlist). Features are added one step at a time; placeholder routes in `app.py` indicate what is coming in future steps.

## Commands

```bash
# Activate virtualenv first
source venv/bin/activate

# Run the dev server (port 5001, debug mode)
python app.py

# Run all tests
pytest

# Run a single test file
pytest tests/test_db.py

# Run a single test by name
pytest -k "test_function_name"
```

## Architecture

**Entry point:** `app.py` — creates the Flask app and registers all routes. Routes that are not yet implemented return plain-text strings with their step number (e.g. `"Logout — coming in Step 3"`).

**Database layer:** `database/db.py` — the only place that touches SQLite. Three functions students must implement:
- `get_db()` — returns a connection with `row_factory = sqlite3.Row` and `PRAGMA foreign_keys = ON`
- `init_db()` — creates all tables with `CREATE TABLE IF NOT EXISTS`
- `seed_db()` — inserts sample rows for development

The database file is `expense_tracker.db` at the project root (gitignored). It is created at runtime — there is no migration tool.

**Templates:** Jinja2 templates in `templates/`. All pages extend `templates/base.html`, which provides the navbar, footer, and links to `static/css/style.css` and `static/js/main.js`.

**Styling:** A single CSS file at `static/css/style.css` using CSS custom properties defined in `:root`. Design tokens: `--ink` (dark text), `--paper` (background), `--accent` (green `#1a472a`), `--accent-2` (amber). Two font families: `DM Serif Display` (headings) and `DM Sans` (body).

**JavaScript:** `static/js/main.js` is currently empty — students add JS as features are built.

## Step progression

The project is built step by step:
1. Database setup (`database/db.py`) — **current step**
2. Registration (POST `/register`)
3. Login / logout / sessions
4. Profile page
5–9. Expense CRUD (add, edit, delete) and filtering
