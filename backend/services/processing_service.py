import os

import pandas as pd

from services.search_service import search_web
from services.webpage_service import get_webpage_text
from services.extraction_service import extract_data
from services.validation_service import (
    is_empty,
    validate_value,
    sort_dataframe,
)


# Columns this tool adds to the output CSV
STATUS_COLUMN = "Row Status"
WEB_FILLED_COLUMN = "Filled From Web"
STILL_MISSING_COLUMN = "Still Missing"
ISSUES_COLUMN = "Validation Issues"
SOURCE_COLUMN = "Source URL"

META_COLUMNS = [
    STATUS_COLUMN,
    WEB_FILLED_COLUMN,
    STILL_MISSING_COLUMN,
    ISSUES_COLUMN,
    SOURCE_COLUMN,
]

DEFAULT_KEY_COLUMNS = ["product", "company"]

SEARCH_SUFFIX = "Bangladesh"

# How many search results to read before giving up on a row
MAX_PAGES_PER_ROW = 3


# =========================================
# Read file
# =========================================

def read_table(file_path: str) -> pd.DataFrame:

    extension = os.path.splitext(file_path)[1].lower()

    # Read everything as text so phone numbers keep their leading 0
    if extension == ".csv":
        df = pd.read_csv(
            file_path,
            dtype=str,
            encoding="utf-8-sig"
        )

    else:
        df = pd.read_excel(
            file_path,
            dtype=str
        )

    df.columns = [str(column).strip() for column in df.columns]

    # object columns accept both text and numbers
    return df.astype(object)


# =========================================
# Labels (the columns the user wants in the CSV)
# =========================================

def apply_labels(df: pd.DataFrame, labels: list) -> pd.DataFrame:

    clean_labels = []
    seen = set()

    for label in labels:

        label = str(label).strip()

        if not label or label.lower() in seen:
            continue

        if label in META_COLUMNS:
            raise ValueError(
                f"'{label}' is used by the tool, please choose another label"
            )

        seen.add(label.lower())
        clean_labels.append(label)

    if not clean_labels:
        return df

    columns_by_name = {
        str(column).strip().lower(): column
        for column in df.columns
        if column not in META_COLUMNS
    }

    output = pd.DataFrame(index=df.index)

    for label in clean_labels:

        column = columns_by_name.get(label.lower())

        # Label not in the file: empty column, filled from the web later
        output[label] = df[column] if column is not None else None

    return output.astype(object)


# =========================================
# Key columns (used to build the search query)
# =========================================

def resolve_key_columns(df: pd.DataFrame, requested=None) -> list:

    columns_by_name = {
        str(column).strip().lower(): column
        for column in df.columns
        if column not in META_COLUMNS
    }

    if requested:

        missing = [
            name for name in requested
            if name.strip().lower() not in columns_by_name
        ]

        if missing:
            raise ValueError(
                f"Key column not found: {', '.join(missing)}"
            )

        return [
            columns_by_name[name.strip().lower()]
            for name in requested
        ]

    defaults = [
        columns_by_name[name]
        for name in DEFAULT_KEY_COLUMNS
        if name in columns_by_name
    ]

    if defaults:
        return defaults

    if not columns_by_name:
        raise ValueError("The file has no columns")

    # No Product/Company column: use the first column
    return [next(iter(columns_by_name.values()))]


# =========================================
# Mode 2: fill empty cells from the web
# =========================================

def _format_sources(field_sources: dict) -> str:

    fields_by_url = {}

    for field, url in field_sources.items():
        fields_by_url.setdefault(url, []).append(field)

    if len(fields_by_url) == 1:
        return next(iter(fields_by_url))

    return " | ".join(
        f"{url} [{', '.join(fields)}]"
        for url, fields in fields_by_url.items()
    )


def fill_from_web(
    key_values: dict,
    existing_data: dict,
    missing_fields: list
):

    filled = {}
    field_sources = {}
    rejected = []
    last_error = None

    query = " ".join(key_values.values()) + " " + SEARCH_SUFFIX

    print("Searching:", query)

    try:
        search_result = search_web(query)

    except Exception as error:
        return filled, field_sources, rejected, f"Search failed: {error}"

    urls = [
        result.get("url")
        for result in search_result.get("results", [])
        if result.get("url")
    ]

    if not urls:
        return filled, field_sources, rejected, "No search result"

    for url in urls[:MAX_PAGES_PER_ROW]:

        remaining = [
            field for field in missing_fields
            if field not in filled
        ]

        if not remaining:
            break

        print("Reading:", url)

        webpage_text = get_webpage_text(url)

        if not webpage_text or webpage_text.startswith("ERROR"):
            last_error = "Could not read webpage"
            continue

        extracted = extract_data(
            webpage_text=webpage_text,
            existing_data={**existing_data, **filled},
            missing_fields=remaining
        )

        print("Extracted:", extracted)

        if extracted.get("error"):
            last_error = extracted["error"]

            # No point reading more pages when Gemini refuses every request
            if extracted.get("quota_exceeded"):
                break

            continue

        # Match keys to the real column names; ignore anything we did not ask for
        fields_by_key = {
            str(field).strip().lower(): field
            for field in remaining
        }

        for key, value in extracted.items():

            field = fields_by_key.get(str(key).strip().lower())

            if field is None or is_empty(value):
                continue

            ok, cleaned, issue = validate_value(field, value)

            # Never write a value that fails validation
            if not ok:
                rejected.append(
                    f"{field}: web value '{value}' rejected ({issue})"
                )
                continue

            filled[field] = cleaned
            field_sources[field] = url

    return filled, field_sources, rejected, last_error


# =========================================
# Full pipeline
# =========================================

def process_dataframe(
    df: pd.DataFrame,
    labels=None,
    key_columns=None,
    sort_by=None,
    ascending: bool = True
):

    df = df.copy().astype(object)

    if labels:
        df = apply_labels(df, labels)

    data_columns = [
        column for column in df.columns
        if column not in META_COLUMNS
    ]

    key_columns = resolve_key_columns(df, key_columns)

    # A column that is empty in every row cannot be searched with,
    # it is something to fill instead
    empty_everywhere = [
        column for column in key_columns
        if df[column].map(is_empty).all()
    ]

    key_columns = [
        column for column in key_columns
        if column not in empty_everywhere
    ]

    if not key_columns:
        raise ValueError(
            "The search columns are empty in every row "
            f"({', '.join(empty_everywhere)}). Choose columns that "
            "already have data, like Product and Company."
        )

    if sort_by and sort_by not in df.columns:
        raise ValueError(f"Sort column not found: {sort_by}")

    for column in META_COLUMNS:
        df[column] = ""

    df = df.astype(object)

    results = []

    for position, row_index in enumerate(df.index):

        row = df.loc[row_index]

        row_number = position + 1

        key_values = {
            column: str(row[column]).strip()
            for column in key_columns
            if not is_empty(row[column])
        }

        empty_keys = [
            column for column in key_columns
            if column not in key_values
        ]

        existing_data = {
            column: None if is_empty(row[column]) else str(row[column])
            for column in data_columns
        }

        print()
        print("--------------------------------")
        print("Processing row:", row_number, key_values)

        # Mode 1: user data is kept as is, only checked
        issues = []

        for column in data_columns:

            if is_empty(row[column]):
                continue

            ok, _, issue = validate_value(column, row[column])

            if not ok:
                issues.append(f"{column}: {issue}")

        missing_fields = [
            column for column in data_columns
            if is_empty(row[column])
        ]

        filled = {}
        field_sources = {}

        if not missing_fields:
            status = "Complete (user data)"

        elif empty_keys:
            # Searching with only part of the key finds the wrong item
            status = (
                "Skipped: key column empty "
                f"({', '.join(empty_keys)})"
            )

        else:

            # Mode 2: only empty cells are searched and filled
            filled, field_sources, rejected, error = fill_from_web(
                key_values,
                existing_data,
                missing_fields
            )

            issues.extend(rejected)

            for column, value in filled.items():
                df.at[row_index, column] = value
                print(f"Filled {column} -> {value}")

            if not filled:
                status = error or "Not found on web"

            elif len(filled) == len(missing_fields):
                status = "Completed from web"

            else:
                status = "Partially filled from web"

        still_missing = [
            column for column in missing_fields
            if column not in filled
        ]

        df.at[row_index, STATUS_COLUMN] = status
        df.at[row_index, WEB_FILLED_COLUMN] = ", ".join(filled)
        df.at[row_index, STILL_MISSING_COLUMN] = ", ".join(still_missing)
        df.at[row_index, ISSUES_COLUMN] = "; ".join(issues)
        df.at[row_index, SOURCE_COLUMN] = (
            _format_sources(field_sources) if field_sources else ""
        )

        results.append({
            "row": row_number,
            "key": " / ".join(key_values.values()),
            "status": status,
            "filled_fields": list(filled),
            "still_missing": still_missing,
            "issues": issues,
            "source_urls": sorted(set(field_sources.values())),
        })

    if sort_by:
        df = sort_dataframe(df, sort_by, ascending)

    return df, results


def save_csv(df: pd.DataFrame, output_path: str):

    # utf-8-sig so Excel shows Bangla text correctly
    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )
