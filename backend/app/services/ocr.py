from pathlib import Path

import fitz
import easyocr
from fastapi import HTTPException

# Singleton: initialize once at module load to avoid reloading models per request
_reader = easyocr.Reader(['en'], gpu=False)


class OCRService:

    def __init__(self):
        self.reader = _reader

    def extract_text(self, file_path: str):

        extension = Path(file_path).suffix.lower()

        try:
            if extension == ".pdf":
                return self.extract_from_pdf(file_path)
            return self.extract_from_image(file_path)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to read file '{Path(file_path).name}': {str(e)}"
            )

    def extract_from_pdf(self, pdf_path: str):

        document = fitz.open(pdf_path)

        text = ""

        for page in document:
            page_text = page.get_text()

            if page_text.strip():
                text += page_text + "\n"

        document.close()

        return text

    def extract_from_image(self, image_path: str):

        result = self.reader.readtext(image_path, detail=0)

        return "\n".join(result)