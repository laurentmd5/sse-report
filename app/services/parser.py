import re

# Modèles Regex pour capturer ND ou Demande, Tâche et Nom Client
TASK_PATTERN = r"(SURVEY\s*PP|SURVEY|RACC(?:ORDEMENT)?|SAV|RIT|PASSAGE|REL[EÉ]VE(?:\s*DE\s*BOITE)?)"

FILENAME_PATTERNS = [
    # Format très spécifique avec tâches connues (ex: 27428786 SURVEY PP abdoulaye Mboup.pdf)
    re.compile(rf"^(\d{{8,15}})[\s\-_]+{TASK_PATTERN}[\s\-_]+(.+)\.pdf$", re.IGNORECASE),
    # Format : Avec "-INL-" spécifique
    re.compile(r"^(\d{8,15})-(Survey|Passage|RIT|reléve)-INL-(.+)\.pdf$", re.IGNORECASE),
    # Format générique : Numéro[-_]Tâche[-_ ]NomClient.pdf
    re.compile(r"^(\d{8,15})[-_]([a-zA-Z0-9\+\s]+?)(?:[-_][a-zA-Z0-9\s\(\)]+)?[-_\s](.+)\.pdf$", re.IGNORECASE)
]

def parse_filename(filename):
    """
    Extrait les données (ND/Demande, Tâche, Client) à partir du nom du fichier PDF.
    """
    clean_filename = filename.strip()
    
    for pattern in FILENAME_PATTERNS:
        match = pattern.match(clean_filename)
        if match:
            num = match.group(1).strip()
            task_type = match.group(2).strip()
            client_name = match.group(3).strip()
            
            nd = None
            demande_no = None
            
            # Déterminer si le numéro est un ND (ex: 33..., 77..., 9 chiffres)
            if re.match(r'^(33|7[05678])\d{7}$', num):
                nd = num
            else:
                demande_no = num
                
            return {
                'success': True,
                'data': {
                    'nd': nd,
                    'demande_no': demande_no,
                    'task_type': task_type,
                    'client_name': client_name
                },
                'message': 'Extraction depuis le nom de fichier réussie.'
            }
            
    return {
        'success': False,
        'data': None,
        'message': 'Le nom du fichier ne correspond à aucun format reconnu.'
    }
