from pathlib import Path

from fastapi import UploadFile

from app.config.settings import settings


class FileService:

    @staticmethod
    async def save_files(files: list[UploadFile]):

        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        uploaded_files = []

        import uuid

        for file in files:
            unique_filename = f"{uuid.uuid4()}_{file.filename}"
            destination = upload_dir / unique_filename

            contents = await file.read()
            with destination.open("wb") as buffer:
                buffer.write(contents)

            uploaded_files.append(
                {
                    "filename": file.filename,
                    "path": str(destination)
                }
            )

        return uploaded_files