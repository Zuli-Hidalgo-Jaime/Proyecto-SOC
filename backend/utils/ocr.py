import pytesseract
from PIL import Image
import pdfplumber
import io

def extract_text_from_image(file_bytes: bytes) -> str:
    """Extrae texto de una imagen usando pytesseract."""
    image = Image.open(io.BytesIO(file_bytes))
    text = pytesseract.image_to_string(image, lang="spa+eng")  # Puedes cambiar idiomas según necesites
    return text.strip()

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extrae texto de todas las páginas de un PDF usando pdfplumber (con fallback a OCR si es imagen)."""
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if not page_text:
                pil_img = page.to_image(resolution=300).original
                page_text = pytesseract.image_to_string(pil_img, lang="spa+eng")
            text += (page_text or "") + "\n"
    return text.strip()

def extract_ocr(file_bytes: bytes, filename: str) -> str:
    """Detecta si es imagen o PDF y llama al método correcto."""
    ext = filename.lower().split(".")[-1]
    if ext in ("jpg", "jpeg", "png", "bmp", "tiff"):
        return extract_text_from_image(file_bytes)
    elif ext == "pdf":
        return extract_text_from_pdf(file_bytes)
    else:
        return ""
