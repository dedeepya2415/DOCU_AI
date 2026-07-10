import fitz
import re
import os
import tempfile
from pathlib import Path
from docx import Document


class TemplateFiller:
    """
    Production-ready template filler that supports:
      - PDF blank templates (underscore detection + redaction)
      - PDF pre-filled documents (search/replace via redaction)
      - DOCX templates (string replacement preserving formatting)
    """

    # ─── Blank Field Extraction (PDF) ───────────────────────────────────

    def extract_blank_fields_from_pdf(self, template_path: str) -> list:
        """
        Scans every page of a PDF for underscore sequences (___+).
        Returns a list of fields with their page, bounding box, and surrounding context.
        """
        doc = fitz.open(template_path)
        all_fields = []

        for page_num, page in enumerate(doc):
            # get_text("words") returns: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
            words = page.get_text("words")

            for i, word_info in enumerate(words):
                x0, y0, x1, y1 = word_info[:4]
                word = word_info[4]

                # Check if this word is a blank (3+ underscores, possibly with trailing punctuation)
                cleaned = word.strip().rstrip(".,;:/-()")
                if not re.match(r"^_{3,}$", cleaned):
                    continue

                # Gather context: up to 5 non-blank words before
                context_before_parts = []
                for j in range(max(0, i - 6), i):
                    w = words[j][4]
                    stripped = w.strip().rstrip(".,;:/-()")
                    if not re.match(r"^_{3,}$", stripped):
                        context_before_parts.append(w)

                # Gather context: up to 5 non-blank words after
                context_after_parts = []
                for j in range(i + 1, min(len(words), i + 6)):
                    w = words[j][4]
                    stripped = w.strip().rstrip(".,;:/-()")
                    if not re.match(r"^_{3,}$", stripped):
                        context_after_parts.append(w)

                all_fields.append({
                    "index": len(all_fields),
                    "page_num": page_num,
                    "blank_text": word.strip(),
                    "context_before": " ".join(context_before_parts),
                    "context_after": " ".join(context_after_parts),
                    "bbox": (x0, y0, x1, y1),
                })

        doc.close()
        return all_fields

    # ─── Detection ──────────────────────────────────────────────────────

    def is_blank_template(self, template_path: str) -> bool:
        """Returns True if the PDF has underscore placeholders."""
        ext = Path(template_path).suffix.lower()
        if ext == ".pdf":
            fields = self.extract_blank_fields_from_pdf(template_path)
            return len(fields) >= 3  # at least 3 blanks to consider it a template
        elif ext == ".docx":
            doc = Document(template_path)
            blank_count = 0
            for paragraph in doc.paragraphs:
                if re.search(r"_{3,}", paragraph.text):
                    blank_count += 1
            return blank_count >= 3
        return False

    # ─── PDF Fill: Blank Fields (by index) ──────────────────────────────

    def fill_pdf_blanks(self, template_path: str, fields: list, field_values: dict) -> str:
        """
        Fills a blank-template PDF by replacing underscore spans at exact bounding boxes.
        Uses dynamic font sizing and Times Roman font for a professional look.
        """
        doc = fitz.open(template_path)

        # 1. Redact all the blanks (paint them white)
        for idx_str, value in field_values.items():
            if not value:
                continue
            idx = int(idx_str)
            if idx >= len(fields):
                continue

            field = fields[idx]
            page = doc[field["page_num"]]
            rect = fitz.Rect(field["bbox"])
            page.add_redact_annot(rect, fill=(1, 1, 1))

        # Apply redactions
        for page in doc:
            page.apply_redactions()

        # 2. Draw the text on top
        for idx_str, value in field_values.items():
            if not value:
                continue
            idx = int(idx_str)
            if idx >= len(fields):
                continue

            field = fields[idx]
            page = doc[field["page_num"]]
            rect = fitz.Rect(field["bbox"])

            # Dynamically calculate font size based on the height of the blank line
            # (Usually height is ~1.2x the font size)
            f_size = max(10, rect.height * 0.9)

            # Insert text using Times Roman (standard for legal docs)
            # We use insert_text with a Point (bottom-left baseline) rather than insert_textbox
            # to avoid text getting clipped or rejected if the bounding box is too tight.
            # Baseline is usually ~15% above the bottom of the bounding box
            baseline_y = rect.y1 - (rect.height * 0.15)
            point = fitz.Point(rect.x0, baseline_y)

            page.insert_text(
                point,
                str(value),
                fontsize=f_size,
                fontname="tiro",
                color=(0, 0, 0)
            )

        fd, temp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        doc.save(temp_path)
        doc.close()
        return temp_path

    # ─── PDF Fill: Pre-filled (search/replace) ──────────────────────────

    def fill_pdf_prefilled(self, template_path: str, mapping_data: dict) -> str:
        """
        Fills a pre-filled PDF by searching for old text and replacing it.
        Uses single-line search to avoid the multi-line search_for bug.
        """
        doc = fitz.open(template_path)
        mappings = mapping_data.get("mappings", [])
        
        insertions = []

        for page_num, page in enumerate(doc):
            for mapping in mappings:
                search_text = mapping.get("search", "")
                replace_text = mapping.get("replace", "")
                if not search_text or not replace_text:
                    continue

                rects = page.search_for(search_text)
                if rects:
                    for rect in rects:
                        # Redact the old text
                        page.add_redact_annot(rect, fill=(1, 1, 1))
                        # Save the insertion details for step 2
                        insertions.append({
                            "page_num": page_num,
                            "rect": rect,
                            "text": replace_text
                        })

        for page in doc:
            page.apply_redactions()

        for ins in insertions:
            page = doc[ins["page_num"]]
            rect = ins["rect"]
            
            f_size = max(10, rect.height * 0.9)
            baseline_y = rect.y1 - (rect.height * 0.15)
            point = fitz.Point(rect.x0, baseline_y)
            
            page.insert_text(
                point,
                ins["text"],
                fontsize=f_size,
                fontname="tiro",
                color=(0, 0, 0)
            )

        fd, temp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        doc.save(temp_path)
        doc.close()
        return temp_path

    # ─── DOCX Fill ──────────────────────────────────────────────────────

    def fill_docx(self, template_path: str, mapping_data: dict) -> str:
        """
        Fills a DOCX template. Supports both blank and pre-filled modes
        via simple string replacement on paragraph text.
        """
        doc = Document(template_path)

        # Determine which key holds the replacements
        if "field_values" in mapping_data:
            # Blank template mode: we need to replace underscores in order
            # Build a list of (underscore_pattern, value) replacements
            field_values = mapping_data["field_values"]
            # Collect all paragraphs text, find underscores, replace by index
            field_idx = 0
            for paragraph in doc.paragraphs:
                if not re.search(r"_{3,}", paragraph.text):
                    continue
                # Find all underscore sequences in this paragraph
                def replace_blank(match):
                    nonlocal field_idx
                    key = str(field_idx)
                    value = field_values.get(key)
                    field_idx += 1
                    return str(value) if value else match.group(0)

                paragraph.text = re.sub(r"_{3,}", replace_blank, paragraph.text)

            # Also handle tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            if not re.search(r"_{3,}", paragraph.text):
                                continue
                            def replace_blank_table(match):
                                nonlocal field_idx
                                key = str(field_idx)
                                value = field_values.get(key)
                                field_idx += 1
                                return str(value) if value else match.group(0)

                            paragraph.text = re.sub(r"_{3,}", replace_blank_table, paragraph.text)

        elif "mappings" in mapping_data:
            # Pre-filled mode: simple search/replace
            mappings = mapping_data["mappings"]
            for paragraph in doc.paragraphs:
                for mapping in mappings:
                    search = mapping.get("search", "")
                    replace = mapping.get("replace", "")
                    if search and replace and search in paragraph.text:
                        paragraph.text = paragraph.text.replace(search, replace)

            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            for mapping in mappings:
                                search = mapping.get("search", "")
                                replace = mapping.get("replace", "")
                                if search and replace and search in paragraph.text:
                                    paragraph.text = paragraph.text.replace(search, replace)

        fd, temp_path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        doc.save(temp_path)
        return temp_path
