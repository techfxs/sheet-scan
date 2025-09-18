import os
import uuid
import time
from fastapi.responses import StreamingResponse
from fastapi import Request
import pandas as pd
import io
from openpyxl import load_workbook

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



PROCESSED_DIR = "processed_files"
os.makedirs(PROCESSED_DIR, exist_ok=True)

@app.post("/uploadcsv")
async def upload_csv(request: Request, file: UploadFile = File(...)):
    start_time = time.time()
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        import re
        columns_to_check = df.columns[:19]
        def summarize_row_errors(row):
            errors = []
            for col in columns_to_check:
                val = row[col]
                if pd.isnull(val):
                    continue
                if re.search(r'[A-Za-z]', str(val)):
                    errors.append(f"{col}: contains alphabets")
            return "; ".join(errors) if errors else ''
        df['ValidationErrors'] = df.apply(summarize_row_errors, axis=1)

        # Save processed file with a unique name
        file_id = str(uuid.uuid4())
        filename = f"{file_id}.csv"
        file_path = os.path.join(PROCESSED_DIR, filename)
        df.to_csv(file_path, index=False)

        # Build file URL
        base_url = str(request.base_url).rstrip("/")
        file_url = f"{base_url}/download/{filename}"

        elapsed = time.time() - start_time
        print(f"Processing time (csv): {elapsed:.2f} seconds")
        return {"file_url": file_url}
    except Exception as e:
        return {"error": str(e)}

# Endpoint to serve the processed file
from fastapi.responses import FileResponse

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(PROCESSED_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='text/csv', filename="processed.csv")
    return {"error": "File not found"}