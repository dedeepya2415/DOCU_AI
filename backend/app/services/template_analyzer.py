import json
import re

from fastapi import HTTPException
from openai import OpenAI

from app.config.settings import settings
from app.prompts.template_prompt import TEMPLATE_FIELD_MAPPING_PROMPT, TEMPLATE_PREFILLED_PROMPT


class TemplateAnalyzer:
    """
    Analyzes legal document templates using an LLM.
    Supports two modes:
      1. Blank templates (indexed field mapping)
      2. Pre-filled documents (search/replace mapping)
    """

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )

    def _call_llm(self, prompt: str) -> dict:
        """Shared LLM call logic with error handling."""
        try:
            response = self.client.chat.completions.create(
                model=settings.OPENROUTER_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=250
            )
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"LLM API error during template analysis: {str(e)}"
            )

        if getattr(response, "error", None):
            raise HTTPException(
                status_code=502,
                detail=f"LLM API error: {response.error.get('message', str(response.error))}"
            )

        content = response.choices[0].message.content

        print("=" * 80)
        print("LLM TEMPLATE ANALYSIS RESPONSE")
        print(content)
        print("=" * 80)

        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise HTTPException(
                status_code=422,
                detail="LLM did not return valid JSON for template analysis."
            )

        try:
            return json.loads(match.group())
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=422,
                detail=f"JSON parse error in template analysis: {str(e)}"
            )

    def analyze_blank_fields(self, fields: list, registry_data: dict) -> dict:
        """
        Mode 1: For blank templates with underscore placeholders.
        Receives a list of extracted blank fields with context, returns field_values by index.
        """
        fields_text = ""
        for field in fields:
            fields_text += (
                f"Field {field['index']}: "
                f"context_before='{field['context_before']}' "
                f"BLANK='{field['blank_text']}' "
                f"context_after='{field['context_after']}'\n"
            )

        prompt = TEMPLATE_FIELD_MAPPING_PROMPT.replace(
            "{fields_list}", fields_text
        ).replace(
            "{registry_data}", json.dumps(registry_data, indent=2)
        )

        return self._call_llm(prompt)

    def analyze_prefilled(self, raw_template_text: str, registry_data: dict) -> dict:
        """
        Mode 2: For pre-filled documents. Uses search/replace approach.
        """
        prompt = TEMPLATE_PREFILLED_PROMPT.replace(
            "{template_text}", raw_template_text
        ).replace(
            "{registry_data}", json.dumps(registry_data, indent=2)
        )

        return self._call_llm(prompt)
