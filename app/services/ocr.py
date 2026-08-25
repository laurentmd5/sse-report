import os
import re
import cv2
import numpy as np
import pymupdf as fitz
import pytesseract
import time
import threading

# Chemin vers l'executable Tesseract
tesseract_cmd = os.environ.get('TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
if os.path.exists(tesseract_cmd):
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

# SEMAPHORE : limite a 1 seul OCR a la fois sur le serveur pour eviter OOM
# Cela evite que 3 workers lancent 3 Tesseract en meme temps
_OCR_LOCK = threading.Semaphore(1)

def preprocess_image(image_bytes):
    """
    Ameliore l'image avec OpenCV pour optimiser l'OCR.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return binary

def extract_pdf_data(pdf_path, target_pages=[0, 1, 2]):
    """
    Extrait le numero de demande, le ND et le nom du client depuis le PDF.
    Optimise pour la production : 3 pages max, DPI reduit, semaphore anti-surcharge.
    """
    start_time = time.time()
    extracted_demande = None
    extracted_nd = None
    extracted_client = None
    confidence = 0
    raw_text_extracted = ""
    error_msg = None

    try:
        pdf_document = fitz.open(pdf_path)

        for page_num in target_pages:
            if page_num >= len(pdf_document):
                break

            page = pdf_document[page_num]

            # DPI reduit de 300 a 150 : 4x moins de pixels = 4x plus rapide
            zoom = 150 / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            processed_img = preprocess_image(pix.tobytes("jpeg"))

            # Timeout Tesseract a 60s + config legere (oem 1 = LSTM uniquement, plus rapide)
            custom_config = r'--oem 1 --psm 6'

            # Acquisition du semaphore : on attend que le precedent soit fini
            acquired = _OCR_LOCK.acquire(timeout=90)
            if not acquired:
                error_msg = "OCR indisponible (surcharge serveur), veuillez reessayer."
                break

            try:
                raw_text = pytesseract.image_to_string(
                    processed_img,
                    lang='fra+eng',
                    config=custom_config,
                    timeout=60  # timeout de 60s par page
                )
            finally:
                _OCR_LOCK.release()

            raw_text_extracted += f"--- Page {page_num+1} ---\n{raw_text}\n"

            # 1. Numero de Demande
            if not extracted_demande:
                demande_patterns = [
                    r'INTERVENTION\s*/\s*(\d{7,15})',
                    r'(?:commande|demande|cmd|order|n\s*°)[^\w]*([A-Z0-9-]{7,15})'
                ]
                for pat in demande_patterns:
                    matches = re.findall(pat, raw_text, re.IGNORECASE)
                    if matches:
                        extracted_demande = matches[0].strip()
                        break
                if not extracted_demande:
                    fallback_matches = re.findall(r'\b(\d{8,10})\b', raw_text)
                    if fallback_matches:
                        extracted_demande = fallback_matches[0]

            # 2. Nom du client
            if not extracted_client:
                client_match = re.search(r'Nom du client[\s:]*([^\n]+)', raw_text, re.IGNORECASE)
                if client_match:
                    name = client_match.group(1).strip()
                    if len(name) > 3:
                        extracted_client = name

            # 3. Numero ND
            if not extracted_nd:
                nd_match_33 = re.search(r'\b(33\d{7})\b', raw_text)
                if nd_match_33:
                    extracted_nd = nd_match_33.group(1)
                else:
                    nd_match_explicit = re.search(r'\bND\b\s*\n?\s*(7[05678]\d{7})\b', raw_text, re.IGNORECASE)
                    if nd_match_explicit:
                        extracted_nd = nd_match_explicit.group(1)
                    else:
                        nd_match_any = re.search(r'\b(7[05678]\d{7})\b', raw_text)
                        if nd_match_any:
                            extracted_nd = nd_match_any.group(1)

            if extracted_demande:
                confidence = 90
                if extracted_nd and extracted_client:
                    break

        pdf_document.close()
        print(f"=== OCR TEXT EXTRACTED ===\n{raw_text_extracted}\n==========================")

    except Exception as e:
        error_msg = f"Erreur OCR: {str(e)}"

    processing_time = int((time.time() - start_time) * 1000)
    print(f"[OCR] Temps de traitement: {processing_time}ms")

    return {
        'success': extracted_demande is not None or extracted_nd is not None,
        'demande_no': extracted_demande,
        'nd': extracted_nd,
        'client_name': extracted_client,
        'confidence': confidence,
        'raw_text': raw_text_extracted,
        'processing_time_ms': processing_time,
        'error': error_msg
    }
