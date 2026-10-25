---
name: pdf-table-extractor
description: Extracts tables from PDF files into CSV or Markdown. Use when the user asks to pull tables or tabular data out of a PDF, or to turn a PDF report into a spreadsheet.
license: MIT
compatibility: Requires Python 3.9+ and the pdfplumber package.
metadata:
  author: shriramkv
  version: "1.0"
allowed-tools: "Bash(python3:*) Read"
---

# PDF table extractor

## Steps

1. Confirm the PDF path and which pages hold the tables.
2. Run the extractor:

   ```bash
   python3 scripts/extract_tables.py report.pdf --pages 1-3 --out tables/
   ```

3. Compare each CSV with the page it came from. The [checking guide](references/checking.md)
   lists the common extraction errors and how to spot them.
4. Return the files with a one-line summary per table.

## Edge cases

- Scanned PDFs have no text layer. Tell the user OCR is needed instead of returning empty tables.
- A table that spans pages comes out as separate CSVs. Merge them only if the headers match.
