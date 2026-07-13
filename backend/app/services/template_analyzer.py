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
            api_key=settings.NVIDIA_API_KEY,
            base_url="https://integrate.api.nvidia.com/v1"
        )

    def _call_llm(self, prompt: str) -> dict:
        """Shared LLM call logic with error handling."""
        print("=" * 80)
        print(f"🚀 [TemplateAnalyzer] Sending request to NVIDIA API (Model: {settings.NVIDIA_MODEL})")
        print(f"📝 Prompt length: {len(prompt)} chars")
        print("=" * 80)

        try:
            response = self.client.chat.completions.create(
                model=settings.NVIDIA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=4096
            )
            print("✅ [TemplateAnalyzer] Successfully received response from NVIDIA API")
        except Exception as e:
            print(f"❌ [TemplateAnalyzer] API call failed: {str(e)}")
            raise HTTPException(
                status_code=502,
                detail=f"LLM API error during template analysis: {str(e)}"
            )

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
            print(f"🪙 [TemplateAnalyzer] Token Usage: Prompt={usage_info.prompt_tokens}, Completion={usage_info.completion_tokens}, Total={usage_info.total_tokens}")

        content = response.choices[0].message.content

        print("=" * 80)
        print("LLM TEMPLATE ANALYSIS RESPONSE")
        print(content)
        print("=" * 80)

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
                        detail=f"JSON parse error in template analysis: {str(e)}\n\nResponse:\n{text}"
                    )

            raise HTTPException(
                status_code=422,
                detail=f"LLM did not return valid JSON for template analysis.\n\nResponse:\n{text}"
            )
            
        return _parse_and_return(content), token_usage

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
