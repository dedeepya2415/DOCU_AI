from app.services.document_processor import DocumentProcessor
from app.services.extractor import AIExtractor

processor = DocumentProcessor()
extractor = AIExtractor()

document = processor.process_document(
    "app/uploads/adhar.jpeg"
)

result = extractor.extract(
    document["raw_text"]
)

print(result)