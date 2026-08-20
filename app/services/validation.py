def validate_extracted_data(parsed_data, ocr_data):
    """
    Détermine le niveau de validation et le score de confiance global.
    Privilégie les données OCR si elles sont trouvées, car le nom de fichier peut être erroné.
    """
    
    is_parsed_ok = parsed_data.get('success', False)
    parsed = parsed_data.get('data', {})
    
    # 1. On prend l'OCR s'il a trouvé, sinon on fallback sur le nom de fichier
    nd = ocr_data.get('nd') or (parsed.get('nd') if is_parsed_ok else None)
    client_name = ocr_data.get('client_name') or (parsed.get('client_name') if is_parsed_ok else None)
    task_type = parsed.get('task_type') if is_parsed_ok else None # L'OCR n'extrait pas la tâche pour l'instant
    
    demande_no = ocr_data.get('demande_no')
    ocr_confidence = ocr_data.get('confidence', 0)
    
    # Calcul du score de confiance global (simplifié)
    base_confidence = 100 if is_parsed_ok else 0
    
    if is_parsed_ok and demande_no:
        global_confidence = int((base_confidence * 0.7) + (ocr_confidence * 0.3))
    elif is_parsed_ok:
        global_confidence = 60 # Manque demande_no
    elif demande_no:
        global_confidence = ocr_confidence # Juste l'OCR
    else:
        global_confidence = 0
        
    # Détermination du statut
    if nd and task_type and client_name and demande_no:
        if global_confidence >= 80:
            status = 'validated' # Auto
            extraction_method = 'filename_ocr'
        else:
            status = 'pending' # Semi-auto (requiert validation humaine)
            extraction_method = 'filename_ocr'
    elif nd and task_type and client_name:
        status = 'pending' # Manuel / Semi-auto
        extraction_method = 'filename_only' if not ocr_data.get('nd') else 'ocr_only'
    else:
        status = 'pending' # Manuel complet
        extraction_method = 'manual'
        
    return {
        'nd': nd,
        'task_type': task_type,
        'client_name': client_name,
        'demande_no': demande_no,
        'confidence_score': global_confidence,
        'validation_status': status,
        'extraction_method': extraction_method
    }
