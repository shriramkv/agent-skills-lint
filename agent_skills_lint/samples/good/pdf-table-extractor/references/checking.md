# Checking extracted tables

- **Merged header cells** often come out as empty strings. Fill them from the cell to the left.
- **Numbers with thousands separators** may split across two columns. Check that each row has
  the same number of cells as the header.
- **Footnote markers** such as * or a superscript digit stick to the value. Strip them before
  converting to numbers.
- **Rotated pages** produce one character per row. Rotate the page before extracting.
