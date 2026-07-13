import json
import re

from fastapi import HTTPException
from openai import OpenAI

from app.config.settings import settings
from app.prompts.extraction_prompt import EXTRACTION_PROMPT


class AIExtractor:

    def __init__(self):

        self.client = OpenAI(
            api_key=settings.NVIDIA_API_KEY,
            base_url="https://integrate.api.nvidia.com/v1"
        )

    def extract(self, raw_text: str):

        prompt = EXTRACTION_PROMPT.replace("{text}", raw_text)

        print("=" * 80)
        print(f"🚀 [AIExtractor] Sending request to NVIDIA API (Model: {settings.NVIDIA_MODEL})")
        print(f"📝 Prompt length: {len(prompt)} chars")
        print("=" * 80)

        try:
            response = self.client.chat.completions.create(
                model=settings.NVIDIA_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=4096
            )
            print("✅ [AIExtractor] Successfully received response from NVIDIA API")
        except Exception as e:
            print(f"❌ [AIExtractor] API call failed: {str(e)}")
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

        usage_info = getattr(response, "usage", None)
        token_usage = {
            "prompt": usage_info.prompt_tokens if usage_info else 0,
            "completion": usage_info.completion_tokens if usage_info else 0,
            "total": usage_info.total_tokens if usage_info else 0
        }
        
        if usage_info:
            print(f"🪙 [AIExtractor] Token Usage: Prompt={usage_info.prompt_tokens}, Completion={usage_info.completion_tokens}, Total={usage_info.total_tokens}")

        content = response.choices[0].message.content

        print("=" * 80)
        print("LLM RESPONSE")
        print(content)
        print("=" * 80)

        # Helper to parse and return
        def _parse_and_return(text):
            # Try direct parse first
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

            # Try to extract from markdown block
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

            # Fallback to broad regex
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError as e:
                    raise HTTPException(
                        status_code=422,
                        detail=f"JSON parse error: {str(e)}\n\nLLM output:\n{text}"
                    )

            raise HTTPException(
                status_code=422,
                detail=f"LLM did not return valid JSON:\n\n{text}"
            )
            
        parsed_data = _parse_and_return(content)
        return parsed_data, token_usage