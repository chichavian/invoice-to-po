import pdfplumber
import io

def extract_text_from_pdf(file):
    """
    Extract text from PDF using pdfplumber for better formatting preservation.
    """
    # Reset file pointer to beginning
    file.seek(0)
    
    # Read the file content
    pdf_content = file.read()
    
    # Create a BytesIO object for pdfplumber
    pdf_stream = io.BytesIO(pdf_content)
    
    # Extract text using pdfplumber
    with pdfplumber.open(pdf_stream) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    
    return text
