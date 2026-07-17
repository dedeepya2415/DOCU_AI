TEMPLATE_SEMANTIC_ANALYSIS_PROMPT = """
You are an expert Indian legal document analyst.

Your task: analyze each blank field in a Sale Deed template and label its SEMANTIC MEANING.
Use ONLY the surrounding context text. NEVER use the field index number to make decisions.

For each field, output:
- "role": who this field belongs to — one of: "seller", "buyer", "property", "skip"
- "field_type": what kind of data goes here — one of:
    name, father_name, dob, gender, age, occupation, address,
    aadhaar, pan, survey_number, sale_price, registration_date,
    area, property_address, date_day, date_month, date_year,
    legal_ref, other
- "reason": one short sentence explaining your decision from the context

ROLE DETECTION RULES (read context_before, context_after, section):
- section="vendor" AND no override in context → role="seller"
- section="buyer" OR context contains "In Favour of" / "Vendee" / "Purchaser" → role="buyer"
- section="property" OR context contains "Survey No" / "Plot No" / "Schedule" → role="property"
- section="preamble" → role="skip" (deed date, execution date, etc.)

FIELD TYPE RULES (from context keywords):
- "Sri/" or "Smt." or "Kum." immediately before [BLANK], AND "S/o" or "D/o" or "W/o" after → name
- "S/o" or "D/o" or "W/o" immediately before [BLANK], AND "aged" after → father_name
- "aged about" before [BLANK], AND "years" after → age  (role=skip, no registry value)
- "Occupation:" before [BLANK] → occupation  (role=skip)
- "D.No" or "Residing" or "Resident of" before or after [BLANK] → address
- "Aadhaar" anywhere in context → aadhaar
- "PAN" anywhere in context → pan
- "day of" or "executed on this" before [BLANK] → date_day  (role=skip)
- "consideration of Rs" or "sum of Rs" before [BLANK] → sale_price
- "Survey No" near [BLANK] → survey_number
- "Village" or "Mandal" or "District" near [BLANK] → property_address
- "document number" or "Book IV" or "volume no" or "power of attorney" in context → legal_ref (role=skip)
- "admeasuring" or "square yards" or "sqmts" near [BLANK] → area

CONFIDENCE RULE:
If you cannot determine the field type with HIGH confidence from context alone, set role="skip" and field_type="other".
Never guess. Never use position as a signal.

Output ONLY valid JSON. No markdown. No explanation outside the JSON.

Output format:
{
  "fields": {
    "0": {"role": "seller", "field_type": "name", "reason": "..."},
    "1": {"role": "seller", "field_type": "father_name", "reason": "..."}
  }
}

BLANK FIELDS TO ANALYZE:
{fields_list}
"""


TEMPLATE_PREFILLED_PROMPT= """
You are an expert Indian legal document analyst.

Your task is to analyze a PRE-FILLED Sale Deed template and extract the existing specific details (names, aadhar, addresses) that belong to the Vendor (seller) and Vendee (buyer) so they can be replaced later.

Do NOT replace anything yet. Create a schema of what strings to search for and their semantic meaning.

For each editable entity you find, output:
- "search_text": The EXACT substring from the raw text to be replaced (e.g., "Vempala Venkata Satyanarayana", "6797 4558 2681"). Keep it perfectly exact. Do NOT include too much surrounding context, just the data value itself.
- "role": "seller" or "buyer" or "property"
- "field_type": name, father_name, age, address, aadhaar, pan, survey_number, sale_price, area, property_address

Output ONLY valid JSON. No markdown. No explanation outside the JSON.

Output format:
{
  "fields": [
    {"search_text": "John Doe", "role": "seller", "field_type": "name"},
    {"search_text": "1234 5678 9012", "role": "seller", "field_type": "aadhaar"}
  ]
}

RAW TEXT:
{template_text}
"""

TEMPLATE_NATIVE_VARIABLES_PROMPT = """
You are an expert Indian legal document generation API.

You will be given a list of EXACT VARIABLE NAMES found inside a Master Jinja2 template (e.g. "seller_name", "vendor_aadhar").
You will also be given the structured REGISTRY DATA containing all extracted information for the seller, buyer, and property.

Your task is to map each requested variable name to the absolutely correct value from the registry data.
Use logical inference on the variable name (e.g., "seller_address" Maps to the address string inside the "seller" JSON blob).
If a variable name does not logically map to any data in the registry, set its value to null.

Output ONLY valid JSON mapping the variable names precisely to the extracted data strings. No markdown. No explanation outside the JSON.

Output format:
{
  "seller_name": "Chitturi Ramakrishna",
  "vendor_aadhar": "1234 5678 9012",
  "unknown_field": null
}

VARIABLE NAMES REQUESTED:
{variables_list}

REGISTRY DATA (for reference):
{registry_data}
"""
