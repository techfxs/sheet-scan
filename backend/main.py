import os
import uuid
import time
import json
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
    expose_headers=["X-Statistics", "Content-Disposition"],
)



PROCESSED_DIR = "processed_files"
os.makedirs(PROCESSED_DIR, exist_ok=True)

@app.post("/uploadcsv")
async def upload_csv(request: Request, file: UploadFile = File(...)):
    start_time = time.time()
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        # Generate statistics about the file
        stats = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "empty_cells_by_column": {},
            "column_names": df.columns.tolist()
        }
        
        # Calculate empty cells by column
        for column in df.columns:
            empty_count = df[column].isna().sum()
            stats["empty_cells_by_column"][column] = int(empty_count)
        
        # Calculate total empty cells
        stats["total_empty_cells"] = sum(stats["empty_cells_by_column"].values())
        
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

        # Count rows with validation errors
        error_rows = df[df['ValidationErrors'] != '']
        stats["rows_with_errors"] = len(error_rows)
        
        # Save processed file with a unique name
        file_id = str(uuid.uuid4())
        filename = f"{file_id}.csv"
        file_path = os.path.join(PROCESSED_DIR, filename)
        df.to_csv(file_path, index=False)

        # Build file URL
        base_url = str(request.base_url).rstrip("/")
        file_url = f"{base_url}/download/{filename}"

        elapsed = time.time() - start_time
        stats["processing_time_seconds"] = round(elapsed, 2)
        print(f"Processing time (csv): {elapsed:.2f} seconds")
        
        return {
            "file_url": file_url,
            "statistics": stats
        }
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


@app.post("/uploadwithpandas")
async def upload_file(file: UploadFile = File(...), request: Request = None):
    start_time = time.time()
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # Generate statistics about the file
        stats = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "empty_cells_by_column": {},
            "column_names": df.columns.tolist()
        }
        
        # Calculate empty cells by column
        for column in df.columns:
            empty_count = df[column].isna().sum()
            stats["empty_cells_by_column"][column] = int(empty_count)
        
        # Calculate total empty cells
        stats["total_empty_cells"] = sum(stats["empty_cells_by_column"].values())
        
        # Example: Add error messages in a new column
        import re
        def summarize_row_errors(row):
            errors = []
            for col in df.columns:
                val = row[col]
                if pd.isnull(val):
                    continue
                if re.search(r'[A-Za-z]', str(val)):
                    errors.append(f"{col}: contains alphabets")
            return "; ".join(errors) if errors else ''
        df['ValidationErrors'] = df.apply(summarize_row_errors, axis=1)
        
        # Count rows with validation errors
        error_rows = df[df['ValidationErrors'] != '']
        stats["rows_with_errors"] = len(error_rows)
        
        # Prepare the Excel file for download
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        # Include statistics in a header
        elapsed = time.time() - start_time
        stats["processing_time_seconds"] = round(elapsed, 2)
        print(f"Processing time (excel): {elapsed:.2f} seconds")
        
        # Add statistics as headers to the response
        headers = {
            'Content-Disposition': 'attachment; filename=processed.xlsx',
            'X-Statistics': json.dumps(stats)
        }
        
        return StreamingResponse(
            output, 
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
            headers=headers
        )
    except Exception as e:
        return {"error": str(e)}