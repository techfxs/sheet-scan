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
        
        def summarize_row_errors(row):
            errors = []
            
            # Validate UPCCASE column (first column)
            if "UPCCASE" in df.columns:
                col = "UPCCASE"
                val = row[col]
                if pd.isnull(val) or str(val).strip() == "":
                    errors.append(f"{col}: cannot be empty")
                else:
                    val_str = str(val).strip()
                    if not val_str.isdigit():
                        errors.append(f"{col}: must contain only numbers")
                    elif len(val_str) != 11:
                        errors.append(f"{col}: must be exactly 11 digits")
            
            # Validate CICID column (second column)
            if "CICID" in df.columns:
                col = "CICID"
                val = row[col]
                if pd.isnull(val) or str(val).strip() == "":
                    errors.append(f"{col}: cannot be empty")
                else:
                    val_str = str(val).strip()
                    if not val_str.isdigit():
                        errors.append(f"{col}: must contain only numbers")
                    elif len(val_str) != 8:
                        errors.append(f"{col}: must be exactly 8 digits")
            
            # Validate Column L (Current Case Cost)
            col_l_index = 11  # Column L is the 12th column (0-indexed)
            if col_l_index < len(df.columns):
                col = df.columns[col_l_index]
                val = row[col]
                if pd.isnull(val) or str(val).strip() == "":
                    errors.append(f"Current Case Cost: cannot be empty")
                else:
                    val_str = str(val).strip()
                    try:
                        float(val_str)
                    except ValueError:
                        errors.append(f"Current Case Cost: must be a number")
            
            # Validate Column M (New Case Cost)
            col_m_index = 12  # Column M is the 13th column (0-indexed)
            if col_m_index < len(df.columns):
                col = df.columns[col_m_index]
                val = row[col]
                if pd.isnull(val) or str(val).strip() == "":
                    errors.append(f"New Case Cost: cannot be empty")
                else:
                    val_str = str(val).strip()
                    try:
                        float(val_str)
                    except ValueError:
                        errors.append(f"New Case Cost: must be a number")
            
            # Validate WareHouse name
            if "Warehouse Name" in df.columns:
                col = "Warehouse Name"
                val = row[col]
                if pd.isnull(val) or str(val).strip() == "":
                    errors.append(f"{col}: cannot be empty")
            
            # Validate Division
            if "Division" in df.columns:
                col = "Division"
                val = row[col]
                if pd.isnull(val) or str(val).strip() == "":
                    errors.append(f"{col}: cannot be empty")
            
            # Validate other columns as before
            columns_to_check = [col for col in df.columns[:19] if col not in ["UPCCASE", "CICID", "Warehouse Name", "Division"]]
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
        
        # Add validation-specific statistics
        stats["validation_summary"] = {
            "total_errors": len(error_rows),
            "error_categories": {}
        }
        
        # Count occurrences of each type of error
        if len(error_rows) > 0:
            all_errors = []
            for errors_str in error_rows['ValidationErrors']:
                if errors_str:
                    all_errors.extend(errors_str.split("; "))
            
            for error in all_errors:
                if ": " in error:
                    error_type = error.split(": ")[1]
                    if error_type in stats["validation_summary"]["error_categories"]:
                        stats["validation_summary"]["error_categories"][error_type] += 1
                    else:
                        stats["validation_summary"]["error_categories"][error_type] = 1
        
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
        
        # Add validation for specific columns
        import re
        def summarize_row_errors(row):
            errors = []
            
            # Validate UPCCASE column (first column)
            if "UPCCASE" in df.columns:
                col = "UPCCASE"
                val = row[col]
                if pd.isnull(val) or str(val).strip() == "":
                    errors.append(f"{col}: cannot be empty")
                else:
                    val_str = str(val).strip()
                    if not val_str.isdigit():
                        errors.append(f"{col}: must contain only numbers")
                    elif len(val_str) != 11:
                        errors.append(f"{col}: must be exactly 11 digits")
            
            # Validate CICID column (second column)
            if "CICID" in df.columns:
                col = "CICID"
                val = row[col]
                if pd.isnull(val) or str(val).strip() == "":
                    errors.append(f"{col}: cannot be empty")
                else:
                    val_str = str(val).strip()
                    if not val_str.isdigit():
                        errors.append(f"{col}: must contain only numbers")
                    elif len(val_str) != 8:
                        errors.append(f"{col}: must be exactly 8 digits")
            
            # Validate Column L (Current Case Cost)
            col_l_index = 11  # Column L is the 12th column (0-indexed)
            if col_l_index < len(df.columns):
                col = df.columns[col_l_index]
                val = row[col]
                if pd.isnull(val) or str(val).strip() == "":
                    errors.append(f"Current Case Cost: cannot be empty")
                else:
                    val_str = str(val).strip()
                    try:
                        float(val_str)
                    except ValueError:
                        errors.append(f"Current Case Cost: must be a number")
            
            # Validate Column M (New Case Cost)
            col_m_index = 12  # Column M is the 13th column (0-indexed)
            if col_m_index < len(df.columns):
                col = df.columns[col_m_index]
                val = row[col]
                if pd.isnull(val) or str(val).strip() == "":
                    errors.append(f"New Case Cost: cannot be empty")
                else:
                    val_str = str(val).strip()
                    try:
                        float(val_str)
                    except ValueError:
                        errors.append(f"New Case Cost: must be a number")
            
            # Validate WareHouse name
            if "Warehouse Name" in df.columns:
                col = "Warehouse Name"
                val = row[col]
                if pd.isnull(val) or str(val).strip() == "":
                    errors.append(f"{col}: cannot be empty")
            
            # Validate Division
            if "Division" in df.columns:
                col = "Division"
                val = row[col]
                if pd.isnull(val) or str(val).strip() == "":
                    errors.append(f"{col}: cannot be empty")
            
            # Validate other columns as before
            other_columns = [col for col in df.columns if col not in ["UPCCASE", "CICID", "WareHouse", "Division"]]
            for col in other_columns:
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
        
        # Add validation-specific statistics
        stats["validation_summary"] = {
            "total_errors": len(error_rows),
            "error_categories": {}
        }
        
        # Count occurrences of each type of error
        if len(error_rows) > 0:
            all_errors = []
            for errors_str in error_rows['ValidationErrors']:
                if errors_str:
                    all_errors.extend(errors_str.split("; "))
            
            for error in all_errors:
                if ": " in error:
                    error_type = error.split(": ")[1]
                    if error_type in stats["validation_summary"]["error_categories"]:
                        stats["validation_summary"]["error_categories"][error_type] += 1
                    else:
                        stats["validation_summary"]["error_categories"][error_type] = 1
        
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