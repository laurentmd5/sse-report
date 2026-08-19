import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app.services.parser import parse_filename
from app.services.ocr import extract_demande_number
from app.services.validation import validate_extracted_data

def test_pdf(filename):
    print(f"\n{'='*50}")
    print(f"Test du fichier : {filename}")
    print(f"{'='*50}")
    
    # 1. Parsing du nom
    parsed_result = parse_filename(filename)
    print("\n--- 1. Résultat Parser Nom de fichier ---")
    print(json.dumps(parsed_result, indent=2, ensure_ascii=False))
    
    # 2. OCR ciblé
    pdf_path = os.path.join(os.path.dirname(__file__), filename)
    print("\n--- 2. Résultat OCR ---")
    ocr_result = extract_demande_number(pdf_path)
    
    # Ne pas afficher tout le texte brut pour ne pas polluer l'écran
    if 'raw_text' in ocr_result:
        del ocr_result['raw_text']
        
    print(json.dumps(ocr_result, indent=2, ensure_ascii=False))
    
    # 3. Validation Globale
    print("\n--- 3. Validation Globale ---")
    validation_result = validate_extracted_data(parsed_result, ocr_result)
    print(json.dumps(validation_result, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    pdfs = [
        "339055955_SURVEY+RIT KHADY NDIAYE.pdf",
        "339683059-Survey-(INL)-Serigne Mbaye  Seck.pdf"
    ]
    
    for pdf in pdfs:
        if os.path.exists(pdf):
            test_pdf(pdf)
        else:
            print(f"Fichier non trouvé : {pdf}")
