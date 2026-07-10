from app.services.ocr import OCRService

ocr = OCRService()

text = ocr.extract_text("app/uploads/adhar.jpeg")

print(text)