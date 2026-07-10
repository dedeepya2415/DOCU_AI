import json
import re

from fastapi import HTTPException
from openai import OpenAI

from app.config.settings import settings
from app.prompts.extraction_prompt import EXTRACTION_PROMPT


class AIExtractor:

    def __init__(self):

        self.client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )

    def extract(self, raw_text: str):

        prompt = EXTRACTION_PROMPT.replace("{text}", raw_text)

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENROUTER_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=600
            )
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"LLM API error: {str(e)}"
            )

        # Check for API errors returned in body
        if getattr(response, "error", None):
            raise HTTPException(
                status_code=502,
                detail=f"LLM API error: {response.error.get('message', str(response.error))}"
            )

        content = response.choices[0].message.content

        print("=" * 80)
        print("LLM RESPONSE")
        print(content)
        print("=" * 80)

        match = re.search(r"\{.*\}", content, re.DOTALL)

        if not match:
            raise HTTPException(
                status_code=422,
                detail=f"LLM did not return valid JSON:\n\n{content}"
            )

        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=422,
                detail=f"JSON parse error: {str(e)}\n\nLLM output:\n{content}"
            )