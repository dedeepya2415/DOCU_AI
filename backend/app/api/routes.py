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


from fastapi import Form
from fastapi.responses import FileResponse
import json
import asyncio
import uuid
from pathlib import Path
from app.services.ocr import OCRService
from app.services.template_analyzer import TemplateAnalyzer
from app.services.template_filler import TemplateFiller
import urllib.parse
import os

@router.post("/generate-document")
async def generate_document(
    template_file: UploadFile = File(...),
    registry_data: str = Form(...)
):
    try:
        registry_json = json.loads(registry_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid registry_data JSON")

    # Save the template file temporarily
    file_id = str(uuid.uuid4())
    ext = Path(template_file.filename).suffix.lower()
    template_path = f"uploads/{file_id}{ext}"
    os.makedirs("uploads", exist_ok=True)

    with open(template_path, "wb") as buffer:
        buffer.write(await template_file.read())

    analyzer = TemplateAnalyzer()
    filler = TemplateFiller()

    # Auto-detect template type: blank (underscores) vs pre-filled
    is_blank = filler.is_blank_template(template_path)

    if is_blank and ext == ".pdf":
        # ── MODE 1: Blank PDF template ──
        # Step 1: Extract all blank fields with bounding boxes
        fields = filler.extract_blank_fields_from_pdf(template_path)

        print(f"[AutoFill] Detected BLANK template with {len(fields)} fields")
        for f in fields:
            print(f"  Field {f['index']}: ...{f['context_before']}  [{f['blank_text']}]  {f['context_after']}...")

        # Step 2: LLM maps fields by index
        mapping_data = await asyncio.to_thread(
            analyzer.analyze_blank_fields, fields, registry_json
        )

        # Step 3: Fill blanks at exact positions
        field_values = mapping_data.get("field_values", {})
        filled_path = filler.fill_pdf_blanks(template_path, fields, field_values)

    elif ext == ".docx":
        # ── MODE: DOCX template (blank or pre-filled) ──
        if is_blank:
            # Extract fields from DOCX for blank template
            # For DOCX we use text-based extraction, same LLM call
            import re as re_mod
            from docx import Document as DocxDocument
            docx_doc = DocxDocument(template_path)
            fields = []
            for paragraph in docx_doc.paragraphs:
                for match in re_mod.finditer(r"_{3,}", paragraph.text):
                    start = max(0, match.start() - 40)
                    end = min(len(paragraph.text), match.end() + 40)
                    fields.append({
                        "index": len(fields),
                        "blank_text": match.group(),
                        "context_before": paragraph.text[start:match.start()].strip(),
                        "context_after": paragraph.text[match.end():end].strip(),
                    })

            mapping_data = await asyncio.to_thread(
                analyzer.analyze_blank_fields, fields, registry_json
            )
        else:
            ocr_service = OCRService()
            raw_text = ocr_service.extract_text(template_path)
            mapping_data = await asyncio.to_thread(
                analyzer.analyze_prefilled, raw_text, registry_json
            )

        filled_path = filler.fill_docx(template_path, mapping_data)

    else:
        # ── MODE 2: Pre-filled PDF ──
        ocr_service = OCRService()
        raw_text = await asyncio.to_thread(ocr_service.extract_text, template_path)

        print(f"[AutoFill] Detected PRE-FILLED template")

        mapping_data = await asyncio.to_thread(
            analyzer.analyze_prefilled, raw_text, registry_json
        )

        filled_path = filler.fill_pdf_prefilled(template_path, mapping_data)

    # Encode mapping data for the frontend header
    mapping_json_str = json.dumps(mapping_data)
    encoded_mapping = urllib.parse.quote(mapping_json_str)

    filename = f"Filled_{template_file.filename}"
    media_type = (
        "application/pdf" if ext == ".pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    return FileResponse(
        path=filled_path,
        filename=filename,
        media_type=media_type,
        headers={
            "Access-Control-Expose-Headers": "X-Template-Mapping, X-Template-File-Id",
            "X-Template-Mapping": encoded_mapping,
            "X-Template-File-Id": f"{file_id}{ext}"
        }
    )

@router.post("/apply-template-edits")
async def apply_template_edits(
    file_id: str = Form(...),
    mapping_data: str = Form(...)
):
    try:
        mapping_json = json.loads(mapping_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid mapping_data JSON")

    template_path = f"uploads/{file_id}"
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail="Template file not found or expired")

    ext = Path(template_path).suffix.lower()
    filler = TemplateFiller()
    
    if ext == ".docx":
        filled_path = filler.fill_docx(template_path, mapping_json)
    elif ext == ".pdf":
        is_blank = filler.is_blank_template(template_path)
        if is_blank:
            # We need to re-extract the exact fields to map the field_values correctly
            fields = filler.extract_blank_fields_from_pdf(template_path)
            field_values = mapping_json.get("field_values", {})
            filled_path = filler.fill_pdf_blanks(template_path, fields, field_values)
        else:
            filled_path = filler.fill_pdf_prefilled(template_path, mapping_json)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    filename = f"Final_{file_id}"
    media_type = (
        "application/pdf" if ext == ".pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    return FileResponse(
        path=filled_path,
        filename=filename,
        media_type=media_type
    )