import os
import json
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)


def extract_data(
    webpage_text: str,
    existing_data: dict,
    missing_fields: list
):

    prompt = f"""
You are an AI data-entry assistant.

Existing product information:

{json.dumps(existing_data, indent=2)}

We need to find these missing fields:

{json.dumps(missing_fields, indent=2)}

Webpage content:

{webpage_text}

Instructions:

1. Extract only information supported by the webpage.
2. Do not change existing information.
3. Do not guess.
4. If information is not available, return null.
5. Return valid JSON only.

Required JSON format:

{{
    "category": null,
    "price": null,
    "website": null
}}
"""

    # Retry up to 3 times
    for attempt in range(3):

        try:

            print(
                f"Gemini request attempt {attempt + 1}/3"
            )

            response = client.chat.completions.create(
                model="gemini-3.8-flash",
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

            result_text = response.choices[0].message.content

            print("Gemini raw response:")
            print(result_text)

            # Remove markdown code fences if Gemini adds them
            result_text = result_text.strip()

            if result_text.startswith("```json"):
                result_text = result_text[7:]

            elif result_text.startswith("```"):
                result_text = result_text[3:]

            if result_text.endswith("```"):
                result_text = result_text[:-3]

            result_text = result_text.strip()

            result = json.loads(result_text)

            return result

        except Exception as error:

            print(
                f"Gemini attempt {attempt + 1} failed:"
            )

            print(error)

            # Wait before retry
            if attempt < 2:
                print("Waiting 3 seconds before retry...")
                time.sleep(3)

    # All attempts failed
    return {
        "error": "Gemini API temporarily unavailable",
        "category": None,
        "price": None,
        "website": None
    }