# Sample handbook document

Place the course PDF here as `company_handbook.pdf`.

The notebook expects a real handbook-style PDF so students can inspect pages, metadata, chunks, and retrieved evidence. The PDF should contain multiple sections, page numbers, policy exceptions, and at least one table. A scanned page can be added later to demonstrate why OCR or a managed document parser is needed.

The notebook does not manually split on Markdown heading characters. It uses LangChain's PDF loader and recursive text splitter, then sends the resulting documents to Chroma.
