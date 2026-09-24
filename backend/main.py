from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import pandas as pd
import os

from services.search_service import search_web
from services.webpage_service import get_webpage_text
from services.extraction_service import extract_data
from services.excel_service import update_excel


app = FastAPI()


# =========================================
# CORS
# =========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================
# Upload folder
# =========================================

UPLOAD_FOLDER = "uploads"

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# =========================================
# Home
# =========================================

@app.get("/")
def home():

    return {
        "message": "AI Data Entry Agent Backend is running"
    }


# =========================================
# Upload Excel
# =========================================

@app.post("/upload-excel")
async def upload_excel(
    file: UploadFile = File(...)
):

    file_path = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    with open(
        file_path,
        "wb"
    ) as buffer:

        buffer.write(
            await file.read()
        )


    df = pd.read_excel(
        file_path
    )


    # =====================================
    # Analyze columns
    # =====================================

    columns = []

    for column in df.columns:

        total_cells = len(
            df[column]
        )

        empty_cells = int(
            df[column].isna().sum()
        )

        filled_cells = (
            total_cells
            - empty_cells
        )

        columns.append({

            "name": column,

            "total": total_cells,

            "filled": filled_cells,

            "empty": empty_cells

        })


    # =====================================
    # Analyze rows
    # =====================================

    rows = []

    for index, row in df.iterrows():

        row_data = {}

        for column in df.columns:

            value = row[column]

            if pd.isna(value):

                row_data[column] = None

            else:

                row_data[column] = str(
                    value
                )


        rows.append({

            "row_number": index + 1,

            "data": row_data

        })


    return {

        "filename": file.filename,

        "total_rows": len(df),

        "total_columns": len(
            df.columns
        ),

        "columns": columns,

        "rows": rows

    }


# =========================================
# Search
# =========================================

@app.get("/search")
def search(query: str):

    results = search_web(
        query
    )

    return results


# =========================================
# Search Row
# =========================================

@app.get("/search-row")
def search_row(
    product: str,
    company: str
):

    query = (
        f"{product} "
        f"{company} "
        f"Bangladesh"
    )

    results = search_web(
        query
    )

    return {

        "product": product,

        "company": company,

        "query": query,

        "results": results.get(
            "results",
            []
        )

    }


# =========================================
# Read Webpage
# =========================================

@app.get("/read-webpage")
def read_webpage(
    url: str
):

    text = get_webpage_text(
        url
    )

    return {

        "url": url,

        "text": text

    }


# =========================================
# Gemini Extraction
# =========================================

@app.post("/extract-data")
def extract_data_endpoint(
    data: dict
):

    webpage_text = data.get(
        "webpage_text",
        ""
    )

    existing_data = data.get(
        "existing_data",
        {}
    )

    missing_fields = data.get(
        "missing_fields",
        []
    )

    result = extract_data(

        webpage_text=webpage_text,

        existing_data=existing_data,

        missing_fields=missing_fields

    )

    return result


# =========================================
# Manual Excel Update
# =========================================

@app.post("/update-excel")
def update_excel_endpoint(
    data: dict
):

    print(
        "Received data:",
        data
    )

    file_path = data.get(
        "file_path"
    )

    row_index = data.get(
        "row_index"
    )

    extracted_data = data.get(
        "extracted_data",
        {}
    )


    if not file_path:

        return {

            "error":
            "file_path is missing"

        }


    if row_index is None:

        return {

            "error":
            "row_index is missing"

        }


    # Do not update if Gemini failed

    if extracted_data.get(
        "error"
    ):

        return {

            "error":
            "Gemini extraction failed",

            "details":
            extracted_data

        }


    result = update_excel(

        file_path=file_path,

        row_index=int(
            row_index
        ),

        extracted_data=
            extracted_data

    )


    return {

        "message":
        "Excel updated successfully",

        "rows":
        len(result)

    }


# =========================================
# RUN TASK
# =========================================

@app.post("/run-task")
def run_task(
    data: dict
):

    file_path = data.get(
        "file_path"
    )


    if not file_path:

        return {

            "error":
            "file_path is missing"

        }


    # =====================================
    # Read Excel
    # =====================================

    df = pd.read_excel(
        file_path
    )


    print(
        "================================"
    )

    print(
        "Excel loaded successfully"
    )

    print(
        "File:",
        file_path
    )

    print(
        "Columns:",
        df.columns.tolist()
    )

    print(
        "Rows:",
        len(df)
    )

    print(
        "================================"
    )


    results = []


    # =====================================
    # Process every row
    # =====================================

    for row_index, row in df.iterrows():

        product = row.get(
            "Product"
        )

        company = row.get(
            "Company"
        )


        # Product / Company missing

        if (
            pd.isna(product)
            or pd.isna(company)
        ):

            continue


        product = str(
            product
        ).strip()

        company = str(
            company
        ).strip()


        print()
        print(
            "================================"
        )

        print(
            "Processing row:",
            row_index + 1
        )

        print(
            "Product:",
            product
        )

        print(
            "Company:",
            company
        )


        # =================================
        # Find missing fields
        # =================================

        missing_fields = []


        for column in df.columns:

            value = row[column]


            if (
                pd.isna(value)
                or str(value).strip() == ""
            ):

                missing_fields.append(
                    column
                )


        print(
            "Missing fields:",
            missing_fields
        )


        # Nothing missing

        if not missing_fields:

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "Already complete"

            })

            continue


        # =================================
        # Search web
        # =================================

        query = (
            f"{product} "
            f"{company} "
            f"Bangladesh"
        )


        print(
            "Searching:",
            query
        )


        try:

            search_result = search_web(
                query
            )

        except Exception as error:

            print(
                "Search error:",
                error
            )

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "Search failed",

                "error":
                str(error)

            })

            continue


        search_results = (
            search_result.get(
                "results",
                []
            )
        )


        if not search_results:

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "No search result"

            })

            continue


        # =================================
        # Select URL
        # =================================

        first_result = (
            search_results[0]
        )

        url = first_result.get(
            "url"
        )


        if not url:

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "No URL found"

            })

            continue


        print(
            "Selected URL:",
            url
        )


        # =================================
        # Read webpage
        # =================================

        try:

            webpage_text = (
                get_webpage_text(
                    url
                )
            )

        except Exception as error:

            print(
                "Webpage error:",
                error
            )

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "Could not read webpage",

                "url":
                url,

                "error":
                str(error)

            })

            continue


        if (
            not webpage_text
            or webpage_text.startswith(
                "ERROR"
            )
        ):

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "Could not read webpage",

                "url":
                url

            })

            continue


        # =================================
        # Existing data
        # =================================

        existing_data = {}


        for column in df.columns:

            value = row[column]


            if pd.isna(value):

                existing_data[
                    column
                ] = None

            else:

                existing_data[
                    column
                ] = str(value)


        # =================================
        # Gemini extraction
        # =================================

        print(
            "Sending data to Gemini..."
        )


        try:

            extracted_data = extract_data(

                webpage_text=
                    webpage_text,

                existing_data=
                    existing_data,

                missing_fields=
                    missing_fields

            )

        except Exception as error:

            print(
                "Gemini error:",
                error
            )

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "Gemini failed",

                "url":
                url,

                "error":
                str(error)

            })

            continue


        print(
            "Gemini result:",
            extracted_data
        )


        # =================================
        # Gemini failed
        # =================================

        if (
            not extracted_data
            or extracted_data.get(
                "error"
            )
        ):

            print(
                "Gemini failed."
            )

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "Gemini failed",

                "url":
                url,

                "extracted_data":
                extracted_data

            })

            continue


        # =================================
        # Match Excel columns
        # =================================

        normalized_columns = {}


        for column in df.columns:

            normalized_columns[
                str(column)
                .strip()
                .lower()
            ] = column


        excel_ready_data = {}


        for field, value in (
            extracted_data.items()
        ):

            field_normalized = (
                str(field)
                .strip()
                .lower()
            )


            if (
                field_normalized
                not in normalized_columns
            ):

                continue


            actual_column = (
                normalized_columns[
                    field_normalized
                ]
            )


            if value is not None:

                excel_ready_data[
                    actual_column
                ] = value


        # =================================
        # No usable data
        # =================================

        if not excel_ready_data:

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "No usable data extracted",

                "url":
                url,

                "extracted_data":
                extracted_data

            })

            continue


        # =================================
        # Update Excel
        # =================================

        try:

            update_excel(

                file_path=
                    file_path,

                row_index=
                    row_index,

                extracted_data=
                    excel_ready_data

            )

        except Exception as error:

            print(
                "Excel update failed:",
                error
            )

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "Excel update failed",

                "url":
                url,

                "error":
                str(error)

            })

            continue


        results.append({

            "row":
            row_index + 1,

            "product":
            product,

            "status":
            "Updated",

            "url":
            url,

            "extracted_data":
            extracted_data

        })


    return {

        "message":
        "Task completed",

        "results":
        results

    }


# =========================================
# PROCESS EXCEL → NEW CSV
# =========================================

@app.post("/process-excel")
async def process_excel(
    file: UploadFile = File(...)
):

    print(
        "================================"
    )

    print(
        "Processing uploaded file:",
        file.filename
    )

    print(
        "================================"
    )


    # =====================================
    # 1. Save uploaded Excel
    # =====================================

    file_path = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )


    with open(
        file_path,
        "wb"
    ) as buffer:

        buffer.write(
            await file.read()
        )


    # =====================================
    # 2. Read Excel
    # =====================================

    df = pd.read_excel(
        file_path
    )


    print(
        "Original Excel:"
    )

    print(df)


    # =====================================
    # 3. Process each row
    # =====================================

    results = []


    for row_index, row in df.iterrows():

        product = row.get(
            "Product"
        )

        company = row.get(
            "Company"
        )


        # Product / Company missing

        if (
            pd.isna(product)
            or pd.isna(company)
        ):

            results.append({

                "row":
                row_index + 1,

                "status":
                "Skipped",

                "reason":
                "Product or Company missing"

            })

            continue


        product = str(
            product
        ).strip()

        company = str(
            company
        ).strip()


        print()
        print(
            "--------------------------------"
        )

        print(
            "Processing:",
            product
        )

        print(
            "Company:",
            company
        )


        # =================================
        # Find missing fields
        # =================================

        missing_fields = []


        for column in df.columns:

            value = row[column]


            if (
                pd.isna(value)
                or str(value).strip() == ""
            ):

                missing_fields.append(
                    column
                )


        # Already complete

        if not missing_fields:

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "Already complete"

            })

            continue


        print(
            "Missing:",
            missing_fields
        )


        # =================================
        # Search
        # =================================

        query = (
            f"{product} "
            f"{company} "
            f"Bangladesh"
        )


        try:

            search_result = search_web(
                query
            )

            search_results = (
                search_result.get(
                    "results",
                    []
                )
            )

        except Exception as error:

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "Search failed",

                "error":
                str(error)

            })

            continue


        if not search_results:

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "No search result"

            })

            continue


        # =================================
        # Get first URL
        # =================================

        url = search_results[0].get(
            "url"
        )


        if not url:

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "No URL found"

            })

            continue


        print(
            "URL:",
            url
        )


        # =================================
        # Read webpage
        # =================================

        try:

            webpage_text = (
                get_webpage_text(
                    url
                )
            )

        except Exception as error:

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "Webpage read failed",

                "url":
                url,

                "error":
                str(error)

            })

            continue


        if (
            not webpage_text
            or webpage_text.startswith(
                "ERROR"
            )
        ):

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "Webpage read failed",

                "url":
                url

            })

            continue


        # =================================
        # Existing data
        # =================================

        existing_data = {}


        for column in df.columns:

            value = row[column]


            if pd.isna(value):

                existing_data[
                    column
                ] = None

            else:

                existing_data[
                    column
                ] = str(value)


        # =================================
        # Extract
        # =================================

        try:

            extracted_data = extract_data(

                webpage_text=
                    webpage_text,

                existing_data=
                    existing_data,

                missing_fields=
                    missing_fields

            )

        except Exception as error:

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "Gemini failed",

                "url":
                url,

                "error":
                str(error)

            })

            continue


        print(
            "Extracted:",
            extracted_data
        )


        # =================================
        # Gemini failed
        # =================================

        if (
            not extracted_data
            or extracted_data.get(
                "error"
            )
        ):

            results.append({

                "row":
                row_index + 1,

                "product":
                product,

                "status":
                "Gemini failed",

                "url":
                url,

                "extracted_data":
                extracted_data

            })

            continue


        # =================================
        # Match columns
        # =================================

        normalized_columns = {}


        for column in df.columns:

            normalized_columns[
                str(column)
                .strip()
                .lower()
            ] = column


        excel_ready_data = {}


        for field, value in (
            extracted_data.items()
        ):

            field_normalized = (
                str(field)
                .strip()
                .lower()
            )


            if (
                field_normalized
                not in normalized_columns
            ):

                continue


            actual_column = (
                normalized_columns[
                    field_normalized
                ]
            )


            if value is not None:

                excel_ready_data[
                    actual_column
                ] = value


        # =================================
        # Update dataframe directly
        # =================================

        for field, value in (
            excel_ready_data.items()
        ):

            current_value = (
                df.at[
                    row_index,
                    field
                ]
            )


            # IMPORTANT:
            # Only fill empty cells

            if (
                pd.isna(current_value)
                or str(
                    current_value
                ).strip() == ""
            ):

                df.at[
                    row_index,
                    field
                ] = value


                print(
                    f"Filled {field} -> {value}"
                )


        results.append({

            "row":
            row_index + 1,

            "product":
            product,

            "status":
            "Updated",

            "url":
            url,

            "extracted_data":
            extracted_data

        })


    # =====================================
    # 4. Create NEW CSV
    # =====================================

    base_name = os.path.splitext(
        file.filename
    )[0]


    output_filename = (
        base_name
        + "_completed.csv"
    )


    output_path = os.path.join(
        UPLOAD_FOLDER,
        output_filename
    )


    df.to_csv(
        output_path,
        index=False
    )


    print()
    print(
        "================================"
    )

    print(
        "NEW CSV CREATED"
    )

    print(
        "File:",
        output_path
    )

    print(
        "================================"
    )


    # =====================================
    # 5. Return download URL
    # =====================================

    return {

        "message":
        "File processed successfully",

        "filename":
        output_filename,

        "download_url":
        f"/download/{output_filename}",

        "results":
        results

    }


# =========================================
# DOWNLOAD CSV
# =========================================

@app.get("/download/{filename}")
def download_file(
    filename: str
):

    file_path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )


    if not os.path.exists(
        file_path
    ):

        return {

            "error":
            "File not found"

        }


    return FileResponse(

        path=file_path,

        media_type="text/csv",

        filename=filename

    )