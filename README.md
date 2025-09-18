# Simple Vite + React + Flask Excel Upload/Download App

## Frontend

- React app (Vite) in `frontend/`
- Allows user to upload an Excel file
- Shows a download link for the processed file

## Backend

- Flask app in `backend/app.py`
- Accepts Excel file upload at `/upload`
- Processes file (adds a column)
- Returns processed Excel file for download

## How to Run

### Backend

1. In `backend/`, run:

   ```bash
   /Users/home/Desktop/code/sheet-scan/.venv/bin/python app.py
   ```

### Frontend

1. In `frontend/`, run:

   ```bash
   npm run dev
   ```

### Usage

- Open the frontend in your browser (usually http://localhost:5173)
- Upload an Excel file
- Download the processed file returned by the backend

source .venv/bin/activate && uvicorn backend.main:app --reload
