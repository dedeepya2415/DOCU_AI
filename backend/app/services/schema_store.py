import json
import hashlib
import os
from pathlib import Path

SCHEMA_STORE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "template_schemas.json"
)

class TemplateSchemaStore:
    def __init__(self):
        self.store_path = Path(SCHEMA_STORE_PATH)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            with open(self.store_path, "w") as f:
                json.dump({}, f)

    def _get_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of the template file to use as a unique key."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    def get_schema(self, template_path: str) -> dict:
        """Fetch the cached schema for a given template file if it exists."""
        file_hash = self._get_file_hash(template_path)
        try:
            with open(self.store_path, "r") as f:
                store = json.load(f)
            return store.get(file_hash)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def save_schema(self, template_path: str, schema: dict):
        """Save a new schema mapping for a template file."""
        file_hash = self._get_file_hash(template_path)
        try:
            with open(self.store_path, "r") as f:
                store = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            store = {}
            
        store[file_hash] = schema
        
        with open(self.store_path, "w") as f:
            json.dump(store, f, indent=4)
        print(f"✅ [SchemaStore] Saved template schema for hash {file_hash[:8]}")

    def get_tagged_template_path(self, template_path: str) -> str:
        """Returns the file path where the tagged Jinja2 DOCX version of this template will be saved."""
        file_hash = self._get_file_hash(template_path)
        tagged_dir = self.store_path.parent / "tagged_templates"
        tagged_dir.mkdir(exist_ok=True)
        return str(tagged_dir / f"{file_hash}.docx")
