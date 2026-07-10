from app.services.document_processor import DocumentProcessor

processor = DocumentProcessor()

result = processor.process_document(
    "app/uploads/adhar.jpeg"
)

print(result)