import json
import re

from fastapi import HTTPException
from openai import OpenAI

from app.config.settings import settings
from app.prompts.template_prompt import TEMPLATE_SEMANTIC_ANALYSIS_PROMPT, TEMPLATE_PREFILLED_PROMPT


class TemplateAnalyzer:
    """
    Analyzes legal document templates using an LLM in two clean phases:

    Phase 1 — Semantic Labeling (LLM):
        analyze_field_semantics(fields) → schema
        For each blank field, the LLM reads ONLY the surrounding context and assigns
        a role (seller/buyer/property/skip) and a field_type (name/father_name/address/…).
        The registry is NOT passed at this stage — no guessing from data.

    Phase 2 — Deterministic Value Lookup (Python):
        map_registry_values(schema, registry) → field_values dict
        Pure Python lookup table: (role, field_type) → registry path.
        No LLM involved. No position-based heuristics. No hallucination risk.

    Pre-filled documents (search/replace mode):
        analyze_prefilled(raw_text, registry) → mappings
    """

    # ── Registry lookup table ────────────────────────────────────────────
    # Maps (role, field_type) → [registry_section, registry_key]
    # If a combination is not in this table, the field gets None (left blank).
    _REGISTRY_MAP = {
        ("seller",   "name"):              ["seller",   "name"],
        ("seller",   "father_name"):       ["seller",   "father_name"],
        ("seller",   "dob"):               ["seller",   "dob"],
        ("seller",   "gender"):            ["seller",   "gender"],
        ("seller",   "address"):           ["seller",   "address"],
        ("seller",   "aadhaar"):           ["seller",   "aadhaar"],
        ("seller",   "pan"):               ["seller",   "pan"],
        ("buyer",    "name"):              ["buyer",    "name"],
        ("buyer",    "father_name"):       ["buyer",    "father_name"],
        ("buyer",    "dob"):               ["buyer",    "dob"],
        ("buyer",    "gender"):            ["buyer",    "gender"],
        ("buyer",    "address"):           ["buyer",    "address"],
        ("buyer",    "aadhaar"):           ["buyer",    "aadhaar"],
        ("buyer",    "pan"):               ["buyer",    "pan"],
        ("property", "survey_number"):     ["property", "survey_number"],
        ("property", "sale_price"):        ["property", "sale_price"],
        ("property", "registration_date"): ["property", "registration_date"],
        ("property", "area"):              ["property", "area"],
        ("property", "property_address"):  ["property", "property_address"],
        ("property", "seller_name"):       ["seller",   "name"],
        ("property", "buyer_name"):        ["buyer",    "name"],
    }

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.NVIDIA_API_KEY,
            base_url="https://integrate.api.nvidia.com/v1"
        )

    # ── Internal LLM call ────────────────────────────────────────────────

    def _call_llm(self, prompt: str) -> tuple:
        """Shared LLM call with JSON parsing and basic sanitisation."""
        print("=" * 80)
        print(f"🚀 [TemplateAnalyzer] Sending to NVIDIA API (Model: {settings.NVIDIA_MODEL})")
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
            print("✅ [TemplateAnalyzer] Received response")
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
            print(f"🪙 Token Usage: Prompt={usage_info.prompt_tokens}, "
                  f"Completion={usage_info.completion_tokens}, Total={usage_info.total_tokens}")

        content = response.choices[0].message.content

        print("=" * 80)
        print("LLM RESPONSE")
        print(content)
        print("=" * 80)

        # Strip any leading garbage before the first '{'
        brace_pos = content.find("{")
        if brace_pos > 0:
            content = content[brace_pos:]

        def _parse(text):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError as e:
                    raise HTTPException(
                        status_code=422,
                        detail=f"JSON parse error: {str(e)}\n\nResponse:\n{text}"
                    )
            raise HTTPException(
                status_code=422,
                detail=f"LLM did not return valid JSON.\n\nResponse:\n{text}"
            )

        return _parse(content), token_usage

    # ── Phase 1: Semantic Labeling ───────────────────────────────────────

    def analyze_field_semantics(self, fields: list) -> tuple:
        """
        PHASE 1 — LLM semantic analysis.
        Sends only field context (no registry data) and asks the LLM to label
        each blank with role + field_type.

        Returns: (schema_dict, token_usage)
        schema_dict = {"0": {"role": "seller", "field_type": "name", "reason": "..."}, ...}
        """
        fields_text = ""
        for field in fields:
            fields_text += (
                f"Field {field['index']} [section={field.get('section', '?')}]:\n"
                f"  context_before: \"{field['context_before']}\"\n"
                f"  context_after:  \"{field['context_after']}\"\n\n"
            )

        prompt = TEMPLATE_SEMANTIC_ANALYSIS_PROMPT.replace("{fields_list}", fields_text)
        result, token_usage = self._call_llm(prompt)
        # Normalise: the LLM may return {"fields": {...}} or just {"0": {...}}
        schema = result.get("fields", result)
        return schema, token_usage

    # ── Phase 2: Deterministic Registry Lookup ───────────────────────────

    def map_registry_values(self, schema: dict, registry: dict) -> dict:
        """
        PHASE 2 — Pure Python deterministic mapping.
        Given the semantic schema from Phase 1 and the registry data,
        looks up each field's value from the registry using a fixed lookup table.

        No LLM. No guessing. No position-based logic.

        Returns: {"0": "value or None", "1": "value or None", ...}
        """
        field_values = {}
        missing = []

        for idx_str, info in schema.items():
            role = (info.get("role") or "skip").lower().strip()
            field_type = (info.get("field_type") or "other").lower().strip()

            if role == "skip":
                field_values[idx_str] = None
                continue

            lookup_key = (role, field_type)
            if lookup_key in self._REGISTRY_MAP:
                section_key, data_key = self._REGISTRY_MAP[lookup_key]
                value = registry.get(section_key, {}).get(data_key) or None
                field_values[idx_str] = value if value else None
                if not value:
                    missing.append(f"Field {idx_str}: {role}.{field_type}")
            else:
                field_values[idx_str] = None

        print(f"[TemplateAnalyzer] Mapped {len(field_values)} fields. "
              f"Missing values: {len(missing)}")
        if missing:
            print(f"  → Missing: {missing[:10]}")

        return field_values

    # ── Legacy: analyze_blank_fields (kept for DOCX and backwards compat) ─

    def analyze_blank_fields(self, fields: list, registry_data: dict) -> tuple:
        """
        Legacy single-call mode (used by DOCX blank templates).
        Prefer the two-phase approach (analyze_field_semantics + map_registry_values)
        for PDF blank templates.
        """
        fields_text = ""
        for field in fields:
            fields_text += (
                f"Field {field['index']}: "
                f"context_before='{field['context_before']}' "
                f"BLANK='{field['blank_text']}' "
                f"context_after='{field['context_after']}'\n"
            )

        from app.prompts.template_prompt import TEMPLATE_SEMANTIC_ANALYSIS_PROMPT as _SEMANTIC
        # Build a combined prompt for DOCX (still single-call but context-driven)
        combined_prompt = (
            _SEMANTIC.replace("{fields_list}", fields_text)
            + f"\n\nREGISTRY DATA (for reference):\n{json.dumps(registry_data, indent=2)}"
            + "\n\nAlso return field_values mapping: "
              "{\"field_values\": {\"0\": \"value or null\", ...}}"
        )

        result, token_usage = self._call_llm(combined_prompt)

        # If the LLM returned the two-phase schema, convert it
        if "fields" in result and "field_values" not in result:
            schema = result["fields"]
            field_values = self.map_registry_values(schema, registry_data)
            result = {"field_values": field_values}

        return result, token_usage

    # ── Pre-filled documents ─────────────────────────────────────────────

    def analyze_prefilled_semantics(self, raw_template_text: str) -> tuple:
        """
        Mode 2 / Phase 1: Semantic analysis of pre-filled templates.
        Finds exact values in the text that act as placeholders (e.g. John Doe)
        and labels their semantic meaning (role + field_type).
        """
        from app.prompts.template_prompt import TEMPLATE_PREFILLED_PROMPT
        prompt = TEMPLATE_PREFILLED_PROMPT.replace(
            "{template_text}", raw_template_text
        )

        result, token_usage = self._call_llm(prompt)
        schema = result.get("fields", result)
        return schema, token_usage
        
    def map_native_variables(self, template_vars: list, registry_data: dict) -> tuple:
        """
        Mode 3: Natively tagged Master Template support.
        Maps the exact requested Jinja2 variables (e.g. 'seller_name') to
        values from the structured registry JSON data.
        """
        from app.prompts.template_prompt import TEMPLATE_NATIVE_VARIABLES_PROMPT
        
        prompt = TEMPLATE_NATIVE_VARIABLES_PROMPT.replace(
            "{variables_list}", json.dumps(template_vars, indent=2)
        ).replace(
            "{registry_data}", json.dumps(registry_data, indent=2)
        )

        result, token_usage = self._call_llm(prompt)
        # Ensure result only contains the variables requested
        mapped_context = {}
        for var in template_vars:
            mapped_context[var] = result.get(var, None)
            
        print(f"[TemplateAnalyzer] Mapped native Master Template variables:")
        for k, v in mapped_context.items():
            print(f"  {k} -> {str(v)[:30]}...")

        return mapped_context, token_usage

    def map_prefilled_registry_values(self, schema: list, registry: dict) -> dict:
        """
        Mode 2 / Phase 2: Deterministic search/replace mapping.
        Matches the extracted search strings to new values from the registry.
        """
        mappings = []
        missing = []

        for item in schema:
            search_str = item.get("search_text")
            role = (item.get("role") or "").lower().strip()
            field_type = (item.get("field_type") or "").lower().strip()

            if not search_str or not role or not field_type:
                continue

            lookup_key = (role, field_type)
            if lookup_key in self._REGISTRY_MAP:
                section_key, data_key = self._REGISTRY_MAP[lookup_key]
                new_value = registry.get(section_key, {}).get(data_key)
                if new_value:
                    mappings.append({
                        "search": search_str,
                        "replace": str(new_value)
                    })
                else:
                    missing.append(f"{role}.{field_type}")

        print(f"[TemplateAnalyzer] Pre-filled mapped {len(mappings)} fields. "
              f"Missing values: {len(missing)}")

        return {
            "template_name": "Pre-filled Document",
            "mappings": mappings,
            "missing_fields": missing
        }
