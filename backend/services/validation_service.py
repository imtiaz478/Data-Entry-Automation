import re
from urllib.parse import urlparse

import pandas as pd


# =========================================
# Helpers
# =========================================

BANGLA_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

# Column name words -> field type
TYPE_KEYWORDS = {
    "email": {"email", "e-mail", "mail"},
    "phone": {"phone", "mobile", "tel", "telephone", "cell", "whatsapp"},
    "url": {"website", "url", "link", "site", "web"},
    "number": {"price", "cost", "dam", "taka", "tk", "bdt", "amount", "mrp", "rate"},
    "date": {"date", "dob"},
}


def is_empty(value) -> bool:

    if value is None:
        return True

    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass

    return str(value).strip() == ""


def detect_field_type(column: str) -> str:

    words = set(
        re.split(r"[^a-z0-9-]+", str(column).lower())
    )

    for field_type, keywords in TYPE_KEYWORDS.items():
        if words & keywords:
            return field_type

    return "text"


def _format_number(number: float) -> str:

    if number == int(number):
        return str(int(number))

    return str(number)


# =========================================
# Validators
# Each returns (ok, cleaned_value, issue)
# =========================================

def _validate_number(value: str):

    text = value.translate(BANGLA_DIGITS)

    text = re.sub(
        r"(?i)(৳|tk\.?|taka|bdt|/-|,|\s)",
        "",
        text
    )

    if not re.fullmatch(r"\d+(\.\d+)?", text):
        return False, value, "not a single number"

    return True, _format_number(float(text)), None


def _validate_url(value: str):

    text = value.strip()

    if not re.match(r"(?i)^https?://", text):
        text = "https://" + text

    parsed = urlparse(text)

    if (
        parsed.scheme not in ("http", "https")
        or "." not in parsed.netloc
        or " " in text
    ):
        return False, value, "not a valid website link"

    return True, text, None


def _validate_email(value: str):

    text = value.strip()

    if not EMAIL_PATTERN.match(text):
        return False, value, "not a valid email"

    return True, text.lower(), None


def _validate_phone(value: str):

    digits = re.sub(
        r"[^\d]",
        "",
        value.translate(BANGLA_DIGITS)
    )

    # +880 1712... -> 01712...
    if digits.startswith("880"):
        digits = "0" + digits[3:]

    # Mobile: 01XXXXXXXXX, landline: 0 + 8-10 digits
    if (
        re.fullmatch(r"01[3-9]\d{8}", digits)
        or re.fullmatch(r"0\d{8,10}", digits)
    ):
        return True, digits, None

    return False, value, "not a valid Bangladesh phone number"


def _validate_date(value: str):

    parsed = pd.to_datetime(
        value.translate(BANGLA_DIGITS),
        errors="coerce",
        dayfirst=True
    )

    if pd.isna(parsed):
        return False, value, "not a valid date"

    return True, parsed.strftime("%Y-%m-%d"), None


VALIDATORS = {
    "number": _validate_number,
    "url": _validate_url,
    "email": _validate_email,
    "phone": _validate_phone,
    "date": _validate_date,
}


def validate_value(column: str, value):

    if is_empty(value):
        return False, None, "empty"

    text = str(value).strip()

    validator = VALIDATORS.get(
        detect_field_type(column)
    )

    if validator is None:
        return True, text, None

    return validator(text)


# =========================================
# Sorting
# =========================================

def _to_number(value):

    ok, cleaned, _ = _validate_number(str(value))

    return float(cleaned) if ok else None


def sort_dataframe(
    df: pd.DataFrame,
    column: str,
    ascending: bool = True
) -> pd.DataFrame:

    values = df[column]

    filled = values[~values.map(is_empty)]

    numbers = filled.map(_to_number)

    # Sort as numbers only if every filled cell is a number,
    # otherwise "10" would come before "9"
    numeric = len(filled) > 0 and numbers.notna().all()

    def sort_key(series):

        if numeric:
            return series.map(
                lambda v: None if is_empty(v) else _to_number(v)
            ).astype("float64")

        return series.map(
            lambda v: None if is_empty(v) else str(v).strip().lower()
        )

    return df.sort_values(
        by=column,
        key=sort_key,
        ascending=ascending,
        na_position="last",
        kind="stable"
    ).reset_index(drop=True)
