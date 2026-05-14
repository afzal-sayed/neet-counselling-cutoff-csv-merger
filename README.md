# NEET Counselling Cutoff CSV Merger

A Flask web app that merges multiple NEET round-wise Excel/CSV cutoff files into a single unified sheet with fuzzy college-name matching, manual conflict review, and dual CSV/XLSX download.

Supports **NEET PG** and **NEET UG** counselling data.

---

## Features

- Upload up to 5 round files (Round 1, Round 2, Round 3, Stray Vacancy, Sp. Stray Vacancy)
- Drag-and-drop file upload with per-round cards
- Fuzzy college-name matching (handles spelling variants, abbreviations, typos)
  - Matches scoped per state — same college name in different states is never merged
  - High-confidence matches (above threshold) are applied automatically
  - Borderline matches are shown in a review table for manual approve/reject
- Animated progress bar with stage labels
- Dark / light theme toggle (persists across sessions)
- Download output as **XLSX** (two sheets: All Rounds + Match Report) or **CSV**
- No data is written to disk — all processing happens in memory

## Supported Round Mapping

| Upload slot | Output column     |
|-------------|-------------------|
| Round 1     | Round 1           |
| Round 2     | Round 2           |
| Round 3     | Round 3           |
| Round 4     | Stray Vacancy     |
| Round 5     | Sp.Stray Vacancy  |

## Output Format

| Column            | Description                          |
|-------------------|--------------------------------------|
| Allotted Quota    | AI / State / Management quota        |
| Allotted Institute| College name (normalised)            |
| State             | Extracted from college address       |
| Alloted Category  | Open / OBC / SC / ST etc.            |
| Alloted Course    | MD / MS / DNB etc.                   |
| Round 1–3         | AIR cutoff rank for that round       |
| Stray Vacancy     | Cutoff rank for stray vacancy round  |
| Sp.Stray Vacancy  | Cutoff rank for special stray round  |

Missing rounds show `N/A`.

---

## Getting Started

### Requirements

- Python 3.10+
- pip

### Install

```bash
# Linux / macOS
./install.sh

# Windows
install.bat
```

This creates a `.venv` virtual environment and installs all dependencies.

### Run

```bash
# Linux / macOS
./start.sh

# Windows
start.bat
```

Open `http://127.0.0.1:5000` in your browser.

---

## Project Structure

```
neet-counselling-cutoff-csv-merger/
├── app.py                  # Flask app, routes, in-memory job store
├── requirements.txt
├── install.sh / install.bat
├── start.sh / start.bat
├── services/
│   ├── parser.py           # Read .xlsx / .csv into DataFrame
│   ├── normalizer.py       # Column renaming, state extraction, abbreviation expansion
│   ├── matcher.py          # Fuzzy college-name clustering (union-find + rapidfuzz)
│   └── exporter.py         # merge_rounds(), build_xlsx(), build_csv()
├── templates/
│   └── index.html
├── static/
│   ├── css/style.css
│   └── js/app.js
└── tests/
    ├── test_parser.py
    ├── test_normalizer.py
    ├── test_matcher.py
    ├── test_exporter.py
    └── test_routes.py
```

## Running Tests

```bash
# After running install.sh / install.bat
source .venv/bin/activate   # Linux/macOS
# or
.venv\Scripts\activate      # Windows

pytest tests/ -v
```

---

## Tech Stack

- **Backend:** Flask, pandas, openpyxl, xlsxwriter, rapidfuzz
- **Frontend:** Vanilla JS + CSS (no build step)
