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
    
    # 2. Equalize Histogram (Contraste)
    equalized = cv2.equalizeHist(gray)
    
    # 3. Denoise (Median Blur)
    blurred = cv2.medianBlur(equalized, 3)
    
    # 4. Binarisation (Otsu Thresholding)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return binary

def extract_demande_number(pdf_path, target_pages=[0, 1, 2]):
    """
    Extrait le numéro de demande (8-10 chiffres) depuis les premières pages du PDF.
    """
    start_time = time.time()
    extracted_demande = None
    confidence = 0
    raw_text_extracted = ""
    error_msg = None

    try:
        # Ouvrir le PDF
        pdf_document = fitz.open(pdf_path)
        
        # Le pattern cherche une suite d'au moins 8 chiffres (parfois précédé d'espaces/lettres)
        pattern = re.compile(r'\b(\d{8,10})\b')
        
        for page_num in target_pages:
            if page_num >= len(pdf_document):
                break
                
            page = pdf_document[page_num]
            
            # Conversion en image (300 DPI)
            zoom = 300 / 72  # 72 est la valeur par défaut
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Prétraitement de l'image
            processed_img = preprocess_image(pix.tobytes("jpeg"))
            
            # OCR avec Tesseract (psm 6 = Assume a single uniform block of text)
            # langues = fra+eng
            custom_config = r'--oem 3 --psm 6'
            try:
                raw_text = pytesseract.image_to_string(processed_img, lang='fra+eng', config=custom_config)
                raw_text_extracted += f"--- Page {page_num+1} ---\n{raw_text}\n"
                
                # Amélioration de l'extraction : on cherche explicitement "Commande" ou "Demande"
                # suivi de caractères alphanumériques
                advanced_pattern = re.compile(r'(?:commande|demande|cmd|order|n\s*°)[^\w]*([A-Z0-9-]{7,15})', re.IGNORECASE)
                adv_matches = advanced_pattern.findall(raw_text)
                
                if adv_matches:
                    extracted_demande = adv_matches[0]
                    confidence = 90
                    break
                
                # Chercher le pattern basique (8 à 10 chiffres)
                matches = pattern.findall(raw_text)
                if matches:
                    extracted_demande = matches[0]
                    confidence = 80
                    break
            except Exception as e:
                error_msg = f"Erreur Tesseract: {str(e)}"
                break
                
        pdf_document.close()
        print(f"=== OCR TEXT EXTRACTED ===\n{raw_text_extracted}\n==========================")
        
    except Exception as e:
        error_msg = f"Erreur de lecture PDF: {str(e)}"
        
    processing_time = int((time.time() - start_time) * 1000)
    
    return {
        'success': extracted_demande is not None,
        'demande_no': extracted_demande,
        'confidence': confidence,
        'raw_text': raw_text_extracted,
        'processing_time_ms': processing_time,
        'error': error_msg
    }
