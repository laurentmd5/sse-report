import re

# Modèles Regex pour capturer ND, Tâche et Nom Client
FILENAME_PATTERNS = [
    # Format 2 : Avec "-INL-" spécifique
    re.compile(r"^(\d{9,})-(Survey|Passage|RIT|reléve)-INL-(.+)\.pdf$", re.IGNORECASE),
    # Format 1 & 3 & Nouveaux formats : ND[-_]Tâche[-_ ]NomClient.pdf
    # Le séparateur peut être un tiret, un underscore ou un espace
    re.compile(r"^(\d{9,})[-_]([a-zA-Z0-9\+\s]+?)(?:[-_][a-zA-Z0-9\s\(\)]+)?[-_\s](.+)\.pdf$", re.IGNORECASE)
]

def parse_filename(filename):
    """
    Extrait les données (ND, Tâche, Client) à partir du nom du fichier PDF.
    La tâche est récupérée telle quelle.
    """
    clean_filename = filename.strip()
    
    for pattern in FILENAME_PATTERNS:
        match = pattern.match(clean_filename)
        if match:
            nd = match.group(1).strip()
            task_type = match.group(2).strip()
            client_name = match.group(3).strip()
            
            return {
                'success': True,
                'data': {
                    'nd': nd,
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
