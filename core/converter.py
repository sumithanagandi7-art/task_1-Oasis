import os
import tempfile
from pathlib import Path

# Try importing pdf2docx for PDF -> DOCX
try:
    from pdf2docx import Converter
    HAS_PDF2DOCX = True
except ImportError:
    HAS_PDF2DOCX = False


def convert_file(file_stream, filename: str) -> dict:
    """
    Converts a file stream based on its extension.
    Returns a dict with 'success' (bool), 'file_path' (str) and 'error' (str).
    """
    ext = filename.split(".")[-1].lower()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as temp_in:
        temp_in.write(file_stream.read())
        input_path = temp_in.name

    try:
        if ext == "pdf":
            if not HAS_PDF2DOCX:
                return {"success": False, "error": "pdf2docx library is not installed."}
            
            output_path = input_path.replace(".pdf", ".docx")
            cv = Converter(input_path)
            cv.convert(output_path, start=0, end=None)
            cv.close()
            return {"success": True, "file_path": output_path, "filename": filename.replace(".pdf", ".docx")}
            
        elif ext == "docx":
            # Native DOCX to PDF without MS Word is notoriously hard in pure Python.
            # Returning an informative error on Vercel. 
            return {
                "success": False, 
                "error": "DOCX to PDF conversion is not supported natively on Vercel without a third-party Cloud API (like CloudConvert)."
            }
        else:
            return {"success": False, "error": f"Unsupported file extension: {ext}"}

    except Exception as e:
        return {"success": False, "error": str(e)}
