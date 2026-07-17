import asyncio
from fastapi import UploadFile
from fastapi.background import BackgroundTasks
from app.api.routes import generate_document
import os

async def run():
    bt = BackgroundTasks()
    files = [f for f in os.listdir('uploads') if f.endswith('.docx')]
    if files:
        with open('uploads/' + files[0], 'rb') as f:
            file = UploadFile(filename='test.docx', file=f)
            try:
                res = await generate_document(bt, file, '{"mappings": []}')
                print('SUCCESS DOCX')
            except Exception as e:
                import traceback
                traceback.print_exc()
    else:
        print("No DOCX found")

asyncio.run(run())
