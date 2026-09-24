# AI Data Entry Agent

Upload an Excel or CSV file, choose the labels (columns) you want in the
output, and get a completed CSV back.

- **Cells you already filled** are kept as they are and only checked
  (phone, email, website, price, date). No LLM is used for these.
- **Empty cells** (and labels that are not in your file) are filled from
  the web: Tavily finds pages, Gemini reads them, and every value is
  validated before it is written.
- The output CSV has extra columns so you can review the result:
  `Row Status`, `Filled From Web`, `Still Missing`, `Validation Issues`,
  `Source URL`.

## Quick start (Windows)

Double-click `start.bat`. It sets things up the first time, starts the
backend and frontend in two windows, and opens http://localhost:5173.
Keep both windows open while you use the app.

## Setup

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env       # macOS/Linux: cp .env.example .env
```

Put your `TAVILY_API_KEY` and `GEMINI_API_KEY` in `backend/.env`.
Files that are already complete are processed without any keys.

```bash
python main.py
```

Keep this terminal open while you use the app. If the page says
"Could not connect to the backend", this step is not running.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 (use `localhost`, not `127.0.0.1`).
Backend and frontend must both be running, each in its own terminal.

## How a row is processed

1. Your values are validated; problems go to `Validation Issues`
   (your data is never changed).
2. If the row has empty cells, the selected search labels
   (default: `Product` + `Company`) are used to search the web.
   Rows where a search label is empty are skipped.
3. Up to 3 result pages are read. Gemini is asked only for the empty
   fields and must return `null` when a page does not say.
4. Values that fail validation (for example a price range instead of
   one price) are rejected and listed in `Validation Issues`.
5. The table is sorted if you chose a sort label (numbers are sorted
   as numbers), then saved as UTF-8 CSV so Bangla text opens correctly
   in Excel.
