import os
import re
import cv2
import numpy as np
import pymupdf as fitz  # anciennement import fitz
import pytesseract
import time

# Chemin vers l'exécutable Tesseract sous Windows (à ajuster si différent)
# Peut être configuré via la variable d'environnement TESSERACT_CMD
tesseract_cmd = os.environ.get('TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
if os.path.exists(tesseract_cmd):
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

def preprocess_image(image_bytes):
    """
    Améliore l'image avec OpenCV pour optimiser l'OCR.
    """
    # Convertir bytes en array numpy pour OpenCV
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 1. Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Denoise léger
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # 3. Thresholding (Binarisation)
    # Otsu's thresholding fonctionne mieux sans l'égalisation d'histogramme sur des documents scannés
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return binary

def extract_pdf_data(pdf_path, target_pages=[0, 1, 2]):
    """
    Extrait le numéro de demande, le ND et le nom du client depuis le PDF.
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
            zoom = 300 / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            processed_img = preprocess_image(pix.tobytes("jpeg"))
            
            custom_config = r'--oem 3 --psm 6'
            try:
                raw_text = pytesseract.image_to_string(processed_img, lang='fra+eng', config=custom_config)
                raw_text_extracted += f"--- Page {page_num+1} ---\n{raw_text}\n"
                
                # 1. Numéro de Demande (ex: INTERVENTION / 26906456 ou Commande 12345678)
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
                
                # 2. Nom du client (ex: Nom du client \n NDEYE MBENGUE ou Nom du client: abdoulaye Mboup)
                if not extracted_client:
                    client_match = re.search(r'Nom du client[\s:]*([^\n]+)', raw_text, re.IGNORECASE)
                    if client_match:
                        # Nettoyer un peu le nom
                        name = client_match.group(1).strip()
                        if len(name) > 3:
                            extracted_client = name

                # 3. Numéro ND (généralement 9 chiffres commençant par 33)
                if not extracted_nd:
                    # On privilégie un numéro fixe (33) car le mobile (77, etc.) est souvent le "Contact client"
                    nd_match_33 = re.search(r'\b(33\d{7})\b', raw_text)
                    if nd_match_33:
                        extracted_nd = nd_match_33.group(1)
                    else:
                        # Si pas de 33, on cherche le mot ND explicitement suivi d'un numéro
                        nd_match_explicit = re.search(r'\bND\b\s*\n?\s*(7[05678]\d{7})\b', raw_text, re.IGNORECASE)
                        if nd_match_explicit:
                            extracted_nd = nd_match_explicit.group(1)
                        else:
                            # Dernier recours : le premier numéro à 9 chiffres trouvé
                            nd_match_any = re.search(r'\b(7[05678]\d{7})\b', raw_text)
                            if nd_match_any:
                                extracted_nd = nd_match_any.group(1)

                # Si on a trouvé la demande (le plus dur), on augmente la confiance
                if extracted_demande:
                    confidence = 90
                    if extracted_nd and extracted_client:
                        break # On a tout trouvé
                        
            except Exception as e:
                error_msg = f"Erreur Tesseract: {str(e)}"
                break
                
        pdf_document.close()
        print(f"=== OCR TEXT EXTRACTED ===\n{raw_text_extracted}\n==========================")
        
    except Exception as e:
        error_msg = f"Erreur de lecture PDF: {str(e)}"
        
    processing_time = int((time.time() - start_time) * 1000)
    
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
