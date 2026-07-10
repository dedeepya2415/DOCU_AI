from fastapi import HTTPException


class RegistryBuilder:

    def __init__(self):
        self.registry = {
            "seller": {},
            "buyer": {},
            "property": {},
            "financial": {}
        }

    def add_document(self, role: str, data: dict):

        if not isinstance(data, dict):
            raise HTTPException(
                status_code=422,
                detail=f"Extractor returned unexpected type: {type(data).__name__}"
            )

        document_type = data.get("document_type", "")

        if document_type == "aadhaar":

            self.registry[role]["name"] = data.get("name", "")
            self.registry[role]["father_name"] = data.get("father_name", "")
            self.registry[role]["aadhaar"] = data.get("aadhaar_number", "")
            self.registry[role]["address"] = data.get("address", "")

        elif document_type == "pan":

            self.registry[role]["pan"] = data.get("pan_number", "")

        elif document_type in ["sale_deed", "property_passbook"]:

            self.registry["property"] = data

    def build(self):

        return self.registry