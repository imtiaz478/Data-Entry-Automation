import os
import re
import sys
import uuid

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from services.search_service import search_web
from services.webpage_service import get_webpage_text
from services.extraction_service import extract_data
from services.excel_service import update_excel
from services.validation_service import is_empty
from services.processing_service import (
    META_COLUMNS,
    read_table,
    resolve_key_columns,
    process_dataframe,
    save_csv,
)


# Windows consoles default to cp1252, so printing Bangla text crashes
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


app = FastAPI()


# =========================================
# CORS
# =========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================
# Upload folder
# =========================================

UPLOAD_FOLDER = os.path.abspath("uploads")

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}


def safe_upload_path(filename: str) -> str:

    # Only plain file names inside UPLOAD_FOLDER, no "../" or "..\"
    name = os.path.basename(
        str(filename or "").replace("\\", "/")
    )

    if name in ("", ".", ".."):
        raise HTTPException(
            status_code=400,
            detail="Invalid file name"
        )

    path = os.path.abspath(
        os.path.join(UPLOAD_FOLDER, name)
    )

    if os.path.dirname(path) != UPLOAD_FOLDER:
        raise HTTPException(
            status_code=400,
            detail="Invalid file name"
        )

    return path


def save_upload(file: UploadFile) -> str:

    original_name = os.path.basename(
        (file.filename or "").replace("\\", "/")
    )

    base_name, extension = os.path.splitext(original_name)

    extension = extension.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only .xlsx, .xls and .csv files are supported"
        )

    base_name = re.sub(r"[^\w\-]+", "_", base_name).strip("_") or "file"

    # Random prefix so two uploads with the same name do not clash
    stored_name = f"{uuid.uuid4().hex[:8]}_{base_name}{extension}"

    path = safe_upload_path(stored_name)

    with open(path, "wb") as buffer:
        buffer.write(file.file.read())

    return path


def load_table(file_path: str):

    try:
        return read_table(file_path)

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read file: {error}"
        )


def parse_list(value) -> list:

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    return [
        item.strip()
        for item in str(value or "").split(",")
        if item.strip()
    ]


def run_pipeline(
    file_path: str,
    labels: list,
    key_columns: list,
    sort_by: str,
    sort_order: str
):

    df = load_table(file_path)

    print("================================")
    print("Processing file:", os.path.basename(file_path))
    print("Columns:", df.columns.tolist())
    print("Rows:", len(df))
    print("================================")

    try:
        df, results = process_dataframe(
            df,
            labels=labels,
            key_columns=key_columns,
            sort_by=sort_by or None,
            ascending=(sort_order or "asc").lower() != "desc"
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    base_name = os.path.splitext(
        os.path.basename(file_path)
    )[0]

    output_filename = base_name + "_completed.csv"

    save_csv(df, safe_upload_path(output_filename))

    print()
    print("================================")
    print("NEW CSV CREATED:", output_filename)
    print("================================")

    return {
        "message": "File processed successfully",
        "filename": output_filename,
        "download_url": f"/download/{output_filename}",
        "results": results
    }


# =========================================
# Home
# =========================================

@app.get("/")
def home():

    return {
        "message": "AI Data Entry Agent Backend is running"
    }


# =========================================
# Upload file (preview + column list)
# =========================================

@app.post("/upload-excel")
def upload_excel(
    file: UploadFile = File(...)
):

    file_path = save_upload(file)

    df = load_table(file_path)

    data_columns = [
        column for column in df.columns
        if column not in META_COLUMNS
    ]

    # =====================================
    # Analyze columns
    # =====================================

    columns = []

    for column in data_columns:

        empty_cells = int(
            df[column].map(is_empty).sum()
        )

        columns.append({
            "name": column,
            "total": len(df),
            "filled": len(df) - empty_cells,
            "empty": empty_cells
        })

    # =====================================
    # Analyze rows
    # =====================================

    rows = []

    for position, (_, row) in enumerate(df.iterrows()):

        rows.append({
            "row_number": position + 1,
            "data": {
                column: None if is_empty(row[column]) else str(row[column])
                for column in data_columns
            }
        })

    try:
        default_key_columns = resolve_key_columns(df)

    except ValueError:
        default_key_columns = []

    return {
        "filename": file.filename,
        "stored_filename": os.path.basename(file_path),
        "total_rows": len(df),
        "total_columns": len(data_columns),
        "default_key_columns": default_key_columns,
        "columns": columns,
        "rows": rows
    }


# =========================================
# Search
# =========================================

@app.get("/search")
def search(query: str):

    return search_web(query)


# =========================================
# Search Row
# =========================================

@app.get("/search-row")
def search_row(
    product: str,
    company: str
):

    query = f"{product} {company} Bangladesh"

    results = search_web(query)

    return {
        "product": product,
        "company": company,
        "query": query,
        "results": results.get("results", [])
    }


# =========================================
# Read Webpage
# =========================================

@app.get("/read-webpage")
def read_webpage(
    url: str
):

    return {
        "url": url,
        "text": get_webpage_text(url)
    }


# =========================================
# Gemini Extraction
# =========================================

@app.post("/extract-data")
def extract_data_endpoint(
    data: dict
):

    return extract_data(
        webpage_text=data.get("webpage_text", ""),
        existing_data=data.get("existing_data", {}),
        missing_fields=data.get("missing_fields", [])
    )


# =========================================
# Manual Excel Update
# =========================================

@app.post("/update-excel")
def update_excel_endpoint(
    data: dict
):

    print("Received data:", data)

    file_name = data.get("file_path")

    row_index = data.get("row_index")

    extracted_data = data.get("extracted_data", {})

    if not file_name:
        return {"error": "file_path is missing"}

    if row_index is None:
        return {"error": "row_index is missing"}

    # Do not update if Gemini failed
    if extracted_data.get("error"):
        return {
            "error": "Gemini extraction failed",
            "details": extracted_data
        }

    file_path = safe_upload_path(file_name)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    if not file_path.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="Only Excel files can be updated here"
        )

    result = update_excel(
        file_path=file_path,
        row_index=int(row_index),
        extracted_data=extracted_data
    )

    return {
        "message": "Excel updated successfully",
        "rows": len(result)
    }


# =========================================
# RUN TASK (file already uploaded)
# =========================================

@app.post("/run-task")
def run_task(
    data: dict
):

    file_name = data.get("file_path")

    if not file_name:
        return {"error": "file_path is missing"}

    file_path = safe_upload_path(file_name)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    return run_pipeline(
        file_path,
        labels=parse_list(data.get("labels")),
        key_columns=parse_list(data.get("key_columns")),
        sort_by=data.get("sort_by", ""),
        sort_order=data.get("sort_order", "asc")
    )


# =========================================
# PROCESS FILE → NEW CSV
# =========================================

@app.post("/process-excel")
def process_excel(
    file: UploadFile = File(...),
    labels: str = Form(""),
    key_columns: str = Form(""),
    sort_by: str = Form(""),
    sort_order: str = Form("asc")
):

    file_path = save_upload(file)

    return run_pipeline(
        file_path,
        labels=parse_list(labels),
        key_columns=parse_list(key_columns),
        sort_by=sort_by,
        sort_order=sort_order
    )


# =========================================
# DOWNLOAD CSV
# =========================================

@app.get("/download/{filename}")
def download_file(
    filename: str
):

    file_path = safe_upload_path(filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )

    return FileResponse(
        path=file_path,
        media_type="text/csv",
        filename=filename
    )


# =========================================
# python main.py
# =========================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
