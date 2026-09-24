import os
import json
import re
import time

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

load_dotenv()

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
)


# Created on first use, so the server can start without a Gemini key
_client = None


def _get_client():

    global _client

    if _client is None:

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing from .env"
            )

        _client = OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

    return _client


def _parse_json(text: str):

    text = text.strip()

    # Remove markdown code fences if Gemini adds them
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)

    except json.JSONDecodeError:

        # Fall back to the first {...} block in the reply
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end <= start:
            raise

        return json.loads(text[start:end + 1])


def extract_data(
    webpage_text: str,
    existing_data: dict,
    missing_fields: list
):

    if not missing_fields:
        return {}

    # Ask for exactly the columns that are empty in this row
    required_format = {
        field: None
        for field in missing_fields
    }

    prompt = f"""
You are an AI data-entry assistant.

Existing information about the item:

{json.dumps(existing_data, indent=2, ensure_ascii=False)}

We need to find these missing fields:

{json.dumps(missing_fields, indent=2, ensure_ascii=False)}

Webpage content:

{webpage_text}

Instructions:

1. First check that the webpage is about this exact item (same name and
   company/brand as the existing information). A different variant of
   the same brand (another strength, size or version, e.g. "1000 mg"
   when the item is not described that way) counts as a different item.
   If it is not the exact item, return null for every field.
2. Extract only information that is written on the webpage.
3. Do not guess and do not use outside knowledge.
4. If information is not available, return null.
5. Give one short, specific value per field, with no explanations.
   Generic words that fit any product (for example "Medicine",
   "Pharmaceutical", "Product") are not acceptable: return null instead.
6. A field about a website means the official website of the company or
   brand, not a shop, marketplace, news or directory site.
7. Use exactly the keys shown below.
8. Return valid JSON only.

Required JSON format:

{json.dumps(required_format, indent=2, ensure_ascii=False)}
"""

    last_error = None

    # Retry up to 3 times
    for attempt in range(3):

        try:

            print(
                f"Gemini request attempt {attempt + 1}/3"
            )

            response = _get_client().chat.completions.create(
                model=GEMINI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise data extraction assistant."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            result_text = response.choices[0].message.content or ""

            print("Gemini raw response:")
            print(result_text)

            result = _parse_json(result_text)

            if not isinstance(result, dict):
                raise ValueError(
                    "Gemini did not return a JSON object"
                )

            # Map keys back to the exact column names and
            # drop anything we did not ask for
            fields_by_key = {
                str(field).strip().lower(): field
                for field in missing_fields
            }

            return {
                fields_by_key[str(key).strip().lower()]: value
                for key, value in result.items()
                if str(key).strip().lower() in fields_by_key
            }

        except RuntimeError as error:

            # Missing API key: retrying will not help
            return {"error": str(error)}

        except RateLimitError as error:

            message = str(error)

            # Per-minute limit: wait as long as Gemini asks, then retry
            if "PerMinute" in message and attempt < 2:

                match = re.search(r"retry in ([0-9.]+)s", message)

                wait = min(float(match.group(1)) + 1, 65) if match else 30

                print(f"Gemini per-minute limit, waiting {wait:.0f} seconds...")
                time.sleep(wait)
                continue

            # Daily quota used up: retrying only wastes more requests
            print("Gemini quota exceeded:", message)

            return {
                "error": "Gemini daily quota exceeded (free plan limit reached)",
                "quota_exceeded": True
            }

        except Exception as error:

            last_error = error

            print(
                f"Gemini attempt {attempt + 1} failed:"
            )

            print(error)

            # Wait before retry (longer when Gemini is overloaded)
            if attempt < 2:
                wait = 10 * (attempt + 1) if "503" in str(error) else 3
                print(f"Waiting {wait} seconds before retry...")
                time.sleep(wait)

    # All attempts failed
    return {
        "error": f"Gemini request failed: {last_error}"
    }
