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

    # ─── Font Extraction Helpers ────────────────────────────────────────

    def get_font_info_near(self, page, target_rect):
        """
        Extracts actual font size and font name from the text near the target rectangle.
        Returns (font_size, font_name).
        """
        default_size = 12.0
        default_font = "tiro"  # fallback
        
        text_dict = page.get_text("dict")
        best_dist = float('inf')
        best_size = default_size
        best_font = default_font
        
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span_rect = fitz.Rect(span["bbox"])
                        # Check vertical distance
                        dy = min(abs(span_rect.y0 - target_rect.y0), abs(span_rect.y1 - target_rect.y1))
                        if dy < best_dist and span["text"].strip() and not re.match(r"^_{2,}$", span["text"].strip()):
                            best_dist = dy
                            best_size = span["size"]
                            best_font = span["font"]
        
        # Clamp font size as requested (9-14pt)
        best_size = max(9.0, min(14.0, best_size))
        return best_size, self.map_font_name(best_font)

    def map_font_name(self, font_name: str) -> str:
        """
        Maps a detected font name to a PyMuPDF built-in base-14 font.
        """
        name_lower = font_name.lower()
        if "bold" in name_lower and ("italic" in name_lower or "oblique" in name_lower):
            if "times" in name_lower or "serif" in name_lower: return "times-bolditalic"
            if "courier" in name_lower or "mono" in name_lower: return "courier-boldoblique"
            return "helv-boldoblique"
        elif "bold" in name_lower:
            if "times" in name_lower or "serif" in name_lower: return "times-bold"
            if "courier" in name_lower or "mono" in name_lower: return "courier-bold"
            return "helv-bold"
        elif "italic" in name_lower or "oblique" in name_lower:
            if "times" in name_lower or "serif" in name_lower: return "times-italic"
            if "courier" in name_lower or "mono" in name_lower: return "courier-oblique"
            return "helv-oblique"
        else:
            if "times" in name_lower or "serif" in name_lower: return "times-roman"
            if "courier" in name_lower or "mono" in name_lower: return "courier"
            return "helv"

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

            # Use real font info from nearby text
            f_size, f_name = self.get_font_info_near(page, rect)

            from app.services.layout_engine import LayoutEngine
            engine = LayoutEngine(fontname=f_name, default_fontsize=f_size, min_fontsize=8)
            final_fsize, lines = engine.fit_text_to_box(str(value), (rect.x0, rect.y0, rect.x1, rect.y1))

            for line_text, lx, ly in lines:
                page.insert_text(
                    fitz.Point(lx, ly),
                    line_text,
                    fontsize=final_fsize,
                    fontname=f_name,
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
                        # Grab font info before redacting!
                        f_size, f_name = self.get_font_info_near(page, rect)

                        # Redact the old text
                        page.add_redact_annot(rect, fill=(1, 1, 1))
                        # Save the insertion details for step 2
                        insertions.append({
                            "page_num": page_num,
                            "rect": rect,
                            "text": replace_text,
                            "f_size": f_size,
                            "f_name": f_name
                        })

        for page in doc:
            page.apply_redactions()

        for ins in insertions:
            page = doc[ins["page_num"]]
            rect = ins["rect"]
            
            f_size = ins["f_size"]
            f_name = ins["f_name"]
            
            from app.services.layout_engine import LayoutEngine
            engine = LayoutEngine(fontname=f_name, default_fontsize=f_size, min_fontsize=8)
            final_fsize, lines = engine.fit_text_to_box(str(ins["text"]), (rect.x0, rect.y0, rect.x1, rect.y1))

            for line_text, lx, ly in lines:
                page.insert_text(
                    fitz.Point(lx, ly),
                    line_text,
                    fontsize=final_fsize,
                    fontname=f_name,
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

        def replace_regex_in_paragraph(paragraph, pattern, replace_func):
            if not re.search(pattern, paragraph.text):
                return
            
            # Try to replace within individual runs first (safest for formatting)
            matched_in_runs = False
            for run in paragraph.runs:
                if re.search(pattern, run.text):
                    run.text = re.sub(pattern, replace_func, run.text)
                    matched_in_runs = True
            
            if matched_in_runs:
                return

            # Fallback: if the pattern spans multiple runs, collapse into the first run
            # to preserve at least the starting style of the paragraph
            first_run = paragraph.runs[0]
            new_text = re.sub(pattern, replace_func, paragraph.text)
            for run in paragraph.runs:
                run.text = ""
            first_run.text = new_text

        def replace_string_in_paragraph(paragraph, search, replace):
            if search not in paragraph.text:
                return
            
            matched_in_runs = False
            for run in paragraph.runs:
                if search in run.text:
                    run.text = run.text.replace(search, replace)
                    matched_in_runs = True
            
            if matched_in_runs:
                return
                
            first_run = paragraph.runs[0]
            new_text = paragraph.text.replace(search, replace)
            for run in paragraph.runs:
                run.text = ""
            first_run.text = new_text

        # Determine which key holds the replacements
        if "field_values" in mapping_data:
            field_values = mapping_data["field_values"]
            field_idx = 0
            
            def replace_blank(match):
                nonlocal field_idx
                key = str(field_idx)
                value = field_values.get(key)
                field_idx += 1
                return str(value) if value else match.group(0)

            for paragraph in doc.paragraphs:
                replace_regex_in_paragraph(paragraph, r"_{3,}", replace_blank)

            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            replace_regex_in_paragraph(paragraph, r"_{3,}", replace_blank)

        elif "mappings" in mapping_data:
            mappings = mapping_data["mappings"]
            for paragraph in doc.paragraphs:
                for mapping in mappings:
                    search = mapping.get("search", "")
                    replace = mapping.get("replace", "")
                    if search and replace:
                        replace_string_in_paragraph(paragraph, search, replace)

            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            for mapping in mappings:
                                search = mapping.get("search", "")
                                replace = mapping.get("replace", "")
                                if search and replace:
                                    replace_string_in_paragraph(paragraph, search, replace)

        fd, temp_path = tempfile.mkstemp(suffix=".docx")
        os.close(fd)
        doc.save(temp_path)
        return temp_path
