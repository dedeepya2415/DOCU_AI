from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.file_service import FileService
from app.services.document_processor import DocumentProcessor
from app.services.registry_builder import RegistryBuilder

router = APIRouter()


@router.post("/process-documents")
async def process_documents(
    seller_aadhaar: UploadFile = File(...),
    buyer_aadhaar: UploadFile = File(...),
    seller_pan: UploadFile = File(...),
    buyer_pan: UploadFile = File(...),
    property_document: UploadFile = File(...),
):

    uploaded_files = await FileService.save_files([
        seller_aadhaar,
        buyer_aadhaar,
        seller_pan,
        buyer_pan,
        property_document
    ])

    processor = DocumentProcessor()
    registry = RegistryBuilder()

    role_mapping = {
        "seller_aadhaar": "seller",
        "seller_pan": "seller",
        "buyer_aadhaar": "buyer",
        "buyer_pan": "buyer",
        "property_document": "property"
    }

    field_mapping = [
        ("seller_aadhaar",    uploaded_files[0]),
        ("buyer_aadhaar",     uploaded_files[1]),
        ("seller_pan",        uploaded_files[2]),
        ("buyer_pan",         uploaded_files[3]),
        ("property_document", uploaded_files[4]),
    ]

    import asyncio

    async def process_single(field_name, file):
        try:
            result = await asyncio.to_thread(processor.process_document, file["path"])
            return field_name, result, None
        except Exception as e:
            return field_name, None, str(e)

    tasks = [
        process_single(field_name, file)
        for field_name, file in field_mapping
    ]

    results = await asyncio.gather(*tasks)

    errors = {}
    for field_name, result, error in results:
        if error:
            errors[field_name] = error
        else:
            registry.add_document(
                role_mapping[field_name],
                result["structured_data"]
            )

    return {
        "success": len(errors) == 0,
        "registry": registry.build(),
        "errors": errors if errors else None
    }