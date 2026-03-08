# backend/utils/file_processing.py
"""
File processing utilities for extracting text from various formats
"""
import io
from typing import Optional

try:
    import PyPDF2
    import docx
    FILE_PROCESSING_AVAILABLE = True
except ImportError:
    FILE_PROCESSING_AVAILABLE = False


def allowed_file(filename: str, allowed_extensions: set = None) -> bool:
    """Check if file has an allowed extension"""
    if allowed_extensions is None:
        allowed_extensions = {'txt', 'pdf', 'doc', 'docx'}
    
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def extract_text_from_file(file) -> Optional[str]:
    """
    Extract text from uploaded file (TXT, PDF, DOC, DOCX)
    
    Args:
        file: FileStorage object from Flask request
        
    Returns:
        Extracted text or None if extraction fails
    """
    if not FILE_PROCESSING_AVAILABLE:
        raise Exception("File processing libraries not installed. Install python-docx and PyPDF2.")
    
    filename = file.filename.lower()
    
    try:
        if filename.endswith('.txt'):
            return file.read().decode('utf-8', errors='ignore')
        
        elif filename.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
            text = ''
            for page in pdf_reader.pages:
                text += page.extract_text() + '\n'
            return text
        
        elif filename.endswith('.docx'):
            doc = docx.Document(io.BytesIO(file.read()))
            text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            return text
        
        elif filename.endswith('.doc'):
            # Basic DOC support (limited)
            return "DOC format not fully supported. Please use DOCX format."
        
        else:
            return None
            
    except Exception as e:
        print(f"Error extracting text from {filename}: {e}")
        raise Exception(f"Failed to extract text from file: {str(e)}")
