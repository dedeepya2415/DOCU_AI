TEMPLATE_FIELD_MAPPING_PROMPT = """
You are an Indian legal document AI. Map REGISTRY DATA values to numbered blank fields using context clues.

ROLE MAPPINGS: seller=Vendor, buyer=Vendee/Purchaser, property=schedule details.
FIELD MAPPINGS: name=Full Name, father_name=S/o D/o W/o, dob=Date of Birth, aadhaar=Aadhaar No, pan=PAN No, address=Residential Address.

Rules: Never hallucinate. Use null if no data. Output ONLY valid JSON, no markdown.

Output: {"field_values":{"0":"value","1":null},"missing_fields":["desc"]}

BLANK FIELDS:
{fields_list}

REGISTRY DATA:
{registry_data}
"""


TEMPLATE_PREFILLED_PROMPT = """
You are an Indian legal document AI. Replace old Vendor/Purchaser details in RAW TEXT with NEW REGISTRY DATA.

seller=Vendor, buyer=Vendee/Purchaser. Search strings must be EXACT single-line substrings from RAW TEXT. Keep them short (data + 2-3 context words). Never hallucinate. Output ONLY valid JSON.

Output: {"template_name":"Sale Deed","mappings":[{"search":"exact substring","replace":"same with new data"}],"missing_fields":["desc"]}

RAW TEXT:
{template_text}

REGISTRY DATA:
{registry_data}
"""
