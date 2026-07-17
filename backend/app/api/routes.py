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
    
    # Allow up to 3 parallel processes (OCR + LLM) to speed things up without hitting the 5-request NVIDIA limit
    sem = asyncio.Semaphore(3)

    async def process_single(field_name, file):
        async with sem:
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
    total_tokens = {"prompt": 0, "completion": 0, "total": 0}

    for field_name, result, error in results:
        if error:
            errors[field_name] = error
        else:
            registry.add_document(
                role_mapping[field_name],
                result["structured_data"]
            )
            usage = result.get("token_usage")
            if usage:
                total_tokens["prompt"] += usage.get("prompt", 0)
                total_tokens["completion"] += usage.get("completion", 0)
                total_tokens["total"] += usage.get("total", 0)

    return {
        "success": len(errors) == 0,
        "registry": registry.build(),
        "errors": errors if errors else None,
        "token_usage": total_tokens
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
from app.services.schema_store import TemplateSchemaStore
from app.services.document_composer import DocumentComposer
from starlette.background import BackgroundTasks, BackgroundTask
import urllib.parse
import os

@router.post("/generate-document")
async def generate_document(
    template_file: UploadFile = File(...),
    registry_data: str = Form(...)
):
    filled_docx_path = None
    filled_path = None
    try:
        registry_json = json.loads(registry_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid registry_data JSON")

    # Save the template file temporarily
    file_id = str(uuid.uuid4())
    ext = Path(template_file.filename).suffix.lower()
    template_path = f"uploads/{file_id}{ext}"
    
    # We must globally import os and tempfile to avoid shadowing
    import os
    import tempfile
    os.makedirs("uploads", exist_ok=True)

    with open(template_path, "wb") as buffer:
        buffer.write(await template_file.read())

    analyzer = TemplateAnalyzer()
    filler = TemplateFiller()
    schema_store = TemplateSchemaStore()
    composer = DocumentComposer()

    # Auto-detect template type: blank (underscores) vs pre-filled
    is_blank = filler.is_blank_template(template_path)

    if is_blank and ext == ".pdf":
        # ── MODE 1: Blank PDF template — TWO-PHASE SEMANTIC MAPPING ──

        # Phase 1a: Extract blank fields with enriched context + section tracking
        fields = filler.extract_blank_fields_from_pdf(template_path)

        print(f"[AutoFill] Detected BLANK template with {len(fields)} fields")
        for f in fields:
            print(f"  Field {f['index']} [{f.get('section','?')}]: "
                  f"'{f['context_before']}' [BLANK] '{f['context_after']}'")

        # Phase 1b: Caching or LLM
        schema = schema_store.get_schema(template_path)
        token_usage = {}
        
        if schema:
            print(f"⚡ [AutoFill] Loaded cached schema for template (skip LLM analysis)")
        else:
            print(f"[AutoFill] Analyzing template schema for the first time via LLM")
            schema, token_usage = await asyncio.to_thread(
                analyzer.analyze_field_semantics, fields
            )
            schema_store.save_schema(template_path, schema)

        print(f"[AutoFill] Semantic schema:")
        for idx, info in schema.items():
            print(f"  Field {idx}: role={info.get('role')} type={info.get('field_type')} "
                  f"reason={info.get('reason', '')}")

        # Phase 2: Deterministic Python lookup — no LLM, no guessing
        raw_field_values = analyzer.map_registry_values(schema, registry_json)

        # Phase 3: Document Composer (Formatting rules)
        field_values = composer.format_fields(schema, raw_field_values)

        mapping_data = {"field_values": field_values}
        filled_path = filler.fill_pdf_blanks(template_path, fields, field_values)

    elif ext == ".docx":
        # ── MODE 3: Native Master Template (DOCX -> PDF) ──
        # Uploaded .docx MUST be a Master Template containing {{ tags }}
        from docxtpl import DocxTemplate
        import docx2pdf
        
        doc = DocxTemplate(template_path)
        template_vars = list(doc.get_undeclared_variables())
        print(f"[AutoFill] Detected {len(template_vars)} Master Template variables: {template_vars}")
        
        schema = schema_store.get_schema(template_path)
        token_usage = {}
        if schema:
            print(f"⚡ [AutoFill] Loaded cached schema for Master Template")
        else:
            schema, token_usage = await asyncio.to_thread(
                analyzer.map_native_variables, template_vars, registry_json
            )
            schema_store.save_schema(template_path, schema)
            
        # Format dates/currency properly
        formatted_context = composer.format_native_context(schema)
        mapping_data = {"native_context": formatted_context}
        
        # docxtpl renderer
        filled_docx_path = filler.fill_docx(template_path, formatted_context)
        
        # PDF Export
        filled_pdf_fd, filled_path = tempfile.mkstemp(suffix=".pdf")
        os.close(filled_pdf_fd)
        
        print(f"[AutoFill] Exporting populated Master Template to PDF...")
        # docx2pdf uses win32com which requires COM initialization per-thread
        def _convert_to_pdf(in_path, out_path):
            import pythoncom
            pythoncom.CoInitialize()
            try:
                docx2pdf.convert(in_path, out_path)
            finally:
                pythoncom.CoUninitialize()

        await asyncio.to_thread(_convert_to_pdf, filled_docx_path, filled_path)
        print(f"[AutoFill] Master PDF Export Complete.")
        
        # Override extension logic to deliver the PDF
        ext = ".pdf"

    else:
        # ── MODE 2: Pre-filled PDF ──
        ocr_service = OCRService()
        raw_text = await asyncio.to_thread(ocr_service.extract_text, template_path)

        print(f"[AutoFill] Detected PRE-FILLED template")

        schema = schema_store.get_schema(template_path)
        token_usage = {}
        if schema:
            print(f"⚡ [AutoFill] Loaded cached schema for PRE-FILLED PDF template")
        else:
            schema, token_usage = await asyncio.to_thread(
                analyzer.analyze_prefilled_semantics, raw_text
            )
            schema_store.save_schema(template_path, schema)

        mapping_data = analyzer.map_prefilled_registry_values(schema, registry_json)
        # Format the replacements via DocumentComposer
        formatted_mappings = composer.format_prefilled(schema, mapping_data.get("mappings", []))
        mapping_data["mappings"] = formatted_mappings
        
        filled_path = filler.fill_pdf_prefilled(template_path, mapping_data)

    # Encode mapping data for the frontend header
    mapping_json_str = json.dumps(mapping_data)
    encoded_mapping = urllib.parse.quote(mapping_json_str)
    
    token_usage_str = json.dumps(token_usage)

    filename = f"Filled_{template_file.filename}"
    media_type = "application/pdf"

    # Schedule the output and intermediate docx for deletion
    tasks = BackgroundTasks()
    def _unlink_safe(p):
        if p and os.path.exists(p):
            try: os.unlink(p)
            except: pass
            
    tasks.add_task(_unlink_safe, filled_path)
    if filled_docx_path:
        tasks.add_task(_unlink_safe, filled_docx_path)

    return FileResponse(
        path=filled_path,
        filename=filename,
        media_type=media_type,
        background=tasks,
        headers={
            "Access-Control-Expose-Headers": "X-Template-Mapping, X-Template-File-Id, X-Token-Usage",
            "X-Template-Mapping": encoded_mapping,
            "X-Template-File-Id": f"{file_id}{ext}",
            "X-Token-Usage": token_usage_str
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
        filled_path = filler.fill_docx(template_path, mapping_json.get("native_context", mapping_json))
        # Export to PDF? For now just return DOCX. Usually Apply edits is only built for PDFs.
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

    def _unlink_safe2():
        try:
            if os.path.exists(filled_path): os.unlink(filled_path)
        except: pass

    return FileResponse(
        path=filled_path,
        filename=filename,
        media_type=media_type,
        background=BackgroundTask(_unlink_safe2),
        headers={
            "Access-Control-Expose-Headers": "X-Template-File-Id",
            "X-Template-File-Id": file_id
        }
    )
