with open(r"C:\Users\datla\.gemini\antigravity\brain\143b831b-00c3-4afc-9d61-4d9f4a3cda16\task.md", "a", encoding="utf-8") as f:
    f.write("\n- [x] Pivot to Native DOCX Template Generation (Deprecated static PDF parsing due to layout constraints)\n")

with open(r"C:\Users\datla\.gemini\antigravity\brain\143b831b-00c3-4afc-9d61-4d9f4a3cda16\walkthrough.md", "a", encoding="utf-8") as f:
    f.write("\n### Moving Exclusively to Native DOCX Templates\nAs recommended, we have completely abandoned the `PyMuPDF` string-replacement workflow for static PDFs. The intrinsic lack of paragraph reflow mathematically prevents clean document generation when replacing strings with variable-length text (e.g. Indian Addresses). The backend API (`routes.py`) now exclusively accepts Native DOCX Master Templates containing Jinja (`{{ ... }}`) tags, utilizing Microsoft Word's native rendering engine for flawless document assembly and PDF export.\n")
