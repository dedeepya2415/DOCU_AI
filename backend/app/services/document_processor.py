from pathlib import Path

from app.services.ocr import OCRService
from app.services.extractor import AIExtractor


class DocumentProcessor:

    def __init__(self):

        self.ocr = OCRService()
        self.extractor = AIExtractor()

    def process_document(self, file_path: str):

        raw_text = self.ocr.extract_text(file_path)

        structured_data, token_usage = self.extractor.extract(raw_text)

        return {
            "filename": Path(file_path).name,
            "raw_text": raw_text,
            "structured_data": structured_data,
            "token_usage": token_usage
        }