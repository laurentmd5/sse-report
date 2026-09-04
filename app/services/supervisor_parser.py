import os
import re
import openpyxl
from datetime import datetime, date
from app import db
from app.models.team import Team
from app.models.user import User
from app.models.supervisor import TeamAlias

def normalize_text(text):
    """Nettoie et normalise une chaîne de caractères pour la comparaison."""
    if not text:
        return ""
    s = str(text).strip().upper()
    # Remplacer les accents courants
    s = s.replace('É', 'E').replace('È', 'E').replace('Ê', 'E').replace('Ë', 'E')
    s = s.replace('À', 'A').replace('Â', 'A').replace('Ä', 'A')
    s = s.replace('Î', 'I').replace('Ï', 'I')
    s = s.replace('Ô', 'O').replace('Ö', 'O')
    s = s.replace('Û', 'U').replace('Ù', 'U').replace('Ü', 'U')
    s = s.replace('Ç', 'C')
    # Supprimer les espaces multiples et tirets/underscores
    s = re.sub(r'[\-_]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def get_internal_team_keywords():
    """
    Récupère la liste des équipes internes définies en base.
    Renvoie une liste de dictionnaires avec team_id, team_name, leader_name et les alias connus.
    """
    try:
        teams = Team.query.all()
    except Exception:
        return []

    team_data = []
    for t in teams:
        aliases = [normalize_text(a.alias_name) for a in t.aliases.all()]
        leader_name = normalize_text(t.team_leader.full_name) if t.team_leader else ""
        team_name = normalize_text(t.team_name)
        
        team_data.append({
            'team_id': t.id,
            'team_name': t.team_name,
            'norm_team_name': team_name,
            'norm_leader_name': leader_name,
            'aliases': aliases
        })
    return team_data

def match_team_name(raw_name, team_data_cache=None):
    """
    Tente d'associer un nom d'équipe brut trouvé dans un fichier à une équipe interne existante.
    Renvoie un tuple (team_id, is_internal_team).
    """
    if not raw_name:
        return None, False
        
    norm_raw = normalize_text(raw_name)
    if not norm_raw:
        return None, False

    if team_data_cache is None:
        team_data_cache = get_internal_team_keywords()

    # 1. Correspondance exacte sur nom équipe, nom leader ou alias
    for t in team_data_cache:
        if norm_raw == t['norm_team_name'] or norm_raw == t['norm_leader_name'] or norm_raw in t['aliases']:
            return t['team_id'], True

    # 2. Correspondance souple sur les mots-clés clés (Barro, Boukapal, Djiba, Diouf, etc.)
    # Ex: "ABLAYE BOUKAPAL DIOUF" <-> "ABDOULAY BOUPAKAL DIOUF"
    raw_tokens = set(norm_raw.split())
    for t in team_data_cache:
        leader_tokens = set(t['norm_leader_name'].split())
        team_tokens = set(t['norm_team_name'].split())
        
        # Si au moins 2 mots clés importants correspondent
        if len(leader_tokens) >= 2 and len(raw_tokens.intersection(leader_tokens)) >= 2:
            return t['team_id'], True
        if len(team_tokens) >= 2 and len(raw_tokens.intersection(team_tokens)) >= 2:
            return t['team_id'], True
            
        # Cas spécial pour les noms uniques forts
        for strong_token in ['BARRO', 'DJIBA', 'BOUKAPAL', 'BOUPAKAL']:
            if strong_token in raw_tokens and (strong_token in leader_tokens or strong_token in team_tokens):
                return t['team_id'], True

    return None, False


def resync_team_associations():
    """
    Met à jour toutes les entrées existantes en base (Planning, SAV, Récap)
    pour réassocier automatiquement les équipes si de nouvelles équipes ou alias ont été créés après l'import.
    """
    from app.models.supervisor import SupervisorPlanningEntry, SupervisorSAVEntry, SupervisorRecapEntry
    team_data_cache = get_internal_team_keywords()
    
    updated_count = 0
    # 1. Planning
    for entry in SupervisorPlanningEntry.query.all():
        t_id, is_int = match_team_name(entry.raw_team_name, team_data_cache)
        if entry.team_id != t_id or entry.is_internal_team != is_int:
            entry.team_id = t_id
            entry.is_internal_team = is_int
            updated_count += 1
            
    # 2. SAV
    for entry in SupervisorSAVEntry.query.all():
        t_id, is_int = match_team_name(entry.raw_team_name, team_data_cache)
        if entry.team_id != t_id or entry.is_internal_team != is_int:
            entry.team_id = t_id
            entry.is_internal_team = is_int
            updated_count += 1
            
    # 3. Récap
    for entry in SupervisorRecapEntry.query.all():
        t_id, is_int = match_team_name(entry.raw_team_name, team_data_cache)
        if entry.team_id != t_id or entry.is_internal_team != is_int:
            entry.team_id = t_id
            entry.is_internal_team = is_int
            updated_count += 1
            
    if updated_count > 0:
        db.session.commit()
    return updated_count


def parse_planning_excel(file_path):
    """
    Parse un fichier Excel de Planning Global FTTH.
    Renvoie: (list_of_entries, summary_dict)
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    sheet_name = 'PLANNING' if 'PLANNING' in wb.sheetnames else wb.sheetnames[0]
    ws = wb[sheet_name]
    
    headers = [str(c.value).strip() if c.value is not None else '' for c in ws[1]]
    
    # Mapping dynamique des colonnes
    col_map = {}
    for idx, h in enumerate(headers, 1):
        norm_h = normalize_text(h)
        if 'SEGMENT' in norm_h: col_map['segment'] = idx
        elif 'OLT' in norm_h: col_map['olt'] = idx
        elif 'DEMANDE' in norm_h: col_map['demande'] = idx
        elif 'COPER' in norm_h: col_map['coper'] = idx
        elif norm_h == 'ND': col_map['nd'] = idx
        elif 'COMMANDE' in norm_h: col_map['commande_client'] = idx
        elif 'DATEVALIDATION' in norm_h: col_map['date_validation'] = idx
        elif 'NOMDUCLIENT' in norm_h or 'NOM CLIENT' in norm_h: col_map['client_name'] = idx
        elif 'TYPEDELOGEMENT' in norm_h: col_map['type_logement'] = idx
        elif 'CONTACTCLIENT' in norm_h: col_map['contact_client'] = idx
        elif 'DATEDINTERVENTION' in norm_h or 'DATE INTERVENTION' in norm_h: col_map['date_intervention'] = idx
        elif 'HEURE' in norm_h: col_map['heure'] = idx
        elif 'PILOTES' in norm_h: col_map['pilotes'] = idx
        elif norm_h == 'ST': col_map['st'] = idx
        elif 'EQUIPE' in norm_h: col_map['raw_team_name'] = idx
        elif any(k in norm_h for k in ['TACHES', 'TACHE', 'TYPE']): col_map['tache'] = idx

    team_data_cache = get_internal_team_keywords()
    entries = []
    
    for row_idx in range(2, ws.max_row + 1):
        raw_team = str(ws.cell(row=row_idx, column=col_map.get('raw_team_name', 19)).value or '').strip()
        nd_val = str(ws.cell(row=row_idx, column=col_map.get('nd', 5)).value or '').strip()
        demande_val = str(ws.cell(row=row_idx, column=col_map.get('demande', 3)).value or '').strip()
        
        # Ignorer les lignes complètement vides
        if not raw_team and not nd_val and not demande_val:
            continue
            
        team_id, is_internal = match_team_name(raw_team, team_data_cache)
        
        entry = {
            'segment': str(ws.cell(row=row_idx, column=col_map.get('segment', 1)).value or '').strip() or None,
            'olt': str(ws.cell(row=row_idx, column=col_map.get('olt', 2)).value or '').strip() or None,
            'demande': demande_val or None,
            'coper': str(ws.cell(row=row_idx, column=col_map.get('coper', 4)).value or '').strip() or None,
            'nd': nd_val or None,
            'commande_client': str(ws.cell(row=row_idx, column=col_map.get('commande_client', 6)).value or '').strip() or None,
            'date_validation': str(ws.cell(row=row_idx, column=col_map.get('date_validation', 7)).value or '').strip() or None,
            'client_name': str(ws.cell(row=row_idx, column=col_map.get('client_name', 9)).value or '').strip() or None,
            'type_logement': str(ws.cell(row=row_idx, column=col_map.get('type_logement', 11)).value or '').strip() or None,
            'contact_client': str(ws.cell(row=row_idx, column=col_map.get('contact_client', 12)).value or '').strip() or None,
            'date_intervention': str(ws.cell(row=row_idx, column=col_map.get('date_intervention', 13)).value or '').strip() or None,
            'heure': str(ws.cell(row=row_idx, column=col_map.get('heure', 14)).value or '').strip() or None,
            'pilotes': str(ws.cell(row=row_idx, column=col_map.get('pilotes', 17)).value or '').strip() or None,
            'st': str(ws.cell(row=row_idx, column=col_map.get('st', 18)).value or '').strip() or None,
            'raw_team_name': raw_team or 'Non assigné',
            'tache': str(ws.cell(row=row_idx, column=col_map.get('tache', 21)).value or '').strip() or None,
            'team_id': team_id,
            'is_internal_team': is_internal
        }
        entries.append(entry)
        
    return entries


def parse_sav_excel(file_path):
    """
    Parse un fichier Excel d'Instances SAV / Dérangements.
    Renvoie: list_of_entries
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active
    headers = [str(c.value).strip() if c.value is not None else '' for c in ws[1]]
    
    col_map = {}
    for idx, h in enumerate(headers, 1):
        norm_h = normalize_text(h)
        if norm_h == 'ND': col_map['nd'] = idx
        elif 'OFFRE' in norm_h: col_map['offre'] = idx
        elif 'PLAGE' in norm_h: col_map['plage'] = idx
        elif 'DRGT' in norm_h: col_map['id_drgt'] = idx
        elif 'NOM' in norm_h: col_map['nom_client'] = idx
        elif 'PRENOM' in norm_h: col_map['prenom_client'] = idx
        elif 'CONTACT' in norm_h: col_map['contact_client'] = idx
        elif 'ACCES' in norm_h: col_map['acces_rx'] = idx
        elif 'DATE' in norm_h: col_map['date_si'] = idx
        elif 'ZONE' in norm_h: col_map['zone_rs'] = idx
        elif 'COMMUNE' in norm_h: col_map['libelle_commune'] = idx
        elif 'QUARTIER' in norm_h: col_map['libelle_quartier'] = idx
        elif 'PILOTE' in norm_h: col_map['pilotes'] = idx
        elif 'CONSTITUTION' in norm_h: col_map['constitution'] = idx
        elif 'EQUIPE' in norm_h: col_map['raw_team_name'] = idx

    team_data_cache = get_internal_team_keywords()
    entries = []
    
    for row_idx in range(2, ws.max_row + 1):
        raw_team = str(ws.cell(row=row_idx, column=col_map.get('raw_team_name', 14)).value or '').strip()
        nd_val = str(ws.cell(row=row_idx, column=col_map.get('nd', 1)).value or '').strip()
        
        if not raw_team and not nd_val:
            continue
            
        team_id, is_internal = match_team_name(raw_team, team_data_cache)
        
        prenom = str(ws.cell(row=row_idx, column=col_map.get('prenom_client', 6)).value or '').strip()
        nom = str(ws.cell(row=row_idx, column=col_map.get('nom_client', 5)).value or '').strip()
        full_client = f"{prenom} {nom}".strip() or None
        
        entry = {
            'nd': nd_val or None,
            'offre': str(ws.cell(row=row_idx, column=col_map.get('offre', 2)).value or '').strip() or None,
            'plage': str(ws.cell(row=row_idx, column=col_map.get('plage', 3)).value or '').strip() or None,
            'id_drgt': str(ws.cell(row=row_idx, column=col_map.get('id_drgt', 4)).value or '').strip() or None,
            'client_name': full_client,
            'contact_client': str(ws.cell(row=row_idx, column=col_map.get('contact_client', 7)).value or '').strip() or None,
            'acces_rx': str(ws.cell(row=row_idx, column=col_map.get('acces_rx', 8)).value or '').strip() or None,
            'date_si': str(ws.cell(row=row_idx, column=col_map.get('date_si', 9)).value or '').strip() or None,
            'zone_rs': str(ws.cell(row=row_idx, column=col_map.get('zone_rs', 11)).value or '').strip() or None,
            'libelle_commune': str(ws.cell(row=row_idx, column=col_map.get('libelle_commune', 12)).value or '').strip() or None,
            'libelle_quartier': str(ws.cell(row=row_idx, column=col_map.get('libelle_quartier', 13)).value or '').strip() or None,
            'pilotes': str(ws.cell(row=row_idx, column=col_map.get('pilotes', 15)).value or '').strip() or None,
            'constitution': str(ws.cell(row=row_idx, column=col_map.get('constitution', 16)).value or '').strip() or None,
            'raw_team_name': raw_team or 'Non assigné',
            'team_id': team_id,
            'is_internal_team': is_internal
        }
        entries.append(entry)
        
    return entries


def parse_recap_excel(file_path):
    """
    Parse un fichier Excel Récapitulatif (Dashboard Installation Par Équipe).
    Colonnes attendues: Equipe, Nombre de cas, OK (installé), NOK (non installé), Taux % OK
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    ws = wb.active
    
    # Chercher la ligne d'en-tête (souvent ligne 1 ou 2)
    header_row_idx = 1
    col_map = {}
    for r in range(1, min(ws.max_row + 1, 10)):
        row_vals = [str(c.value).strip() if c.value is not None else '' for c in ws[r]]
        norm_vals = [normalize_text(v) for v in row_vals]
        if any('EQUIPE' in v for v in norm_vals) and any(('CAS' in v or 'TOTAL' in v or 'OK' in v) for v in norm_vals):
            header_row_idx = r
            for idx, h in enumerate(norm_vals, 1):
                if 'EQUIPE' in h: col_map['raw_team_name'] = idx
                elif 'CAS' in h or 'TOTAL' in h: col_map['nb_cases'] = idx
                elif 'NOK' in h or 'NON' in h or 'BLOC' in h or 'PASSAGE' in h: col_map['nb_nok'] = idx
                elif 'OK' in h and 'TAUX' not in h and '%' not in h: col_map['nb_ok'] = idx
                elif 'TAUX' in h or '%' in h: col_map['taux_ok'] = idx
            break

    team_data_cache = get_internal_team_keywords()
    entries = []
    
    for row_idx in range(header_row_idx + 1, ws.max_row + 1):
        raw_team = str(ws.cell(row=row_idx, column=col_map.get('raw_team_name', 1)).value or '').strip()
        if not raw_team or normalize_text(raw_team) in ['TOTAL', 'TOTAL GENERAL', 'SOMME']:
            continue
            
        team_id, is_internal = match_team_name(raw_team, team_data_cache)
        
        def safe_int(val):
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return 0
                
        def safe_float_pct(val):
            try:
                if isinstance(val, (int, float)):
                    return round(val * 100 if val <= 1.0 else val, 1)
                s = str(val).replace('%', '').replace(',', '.').strip()
                return round(float(s), 1)
            except (ValueError, TypeError):
                return 0.0

        nb_cases = safe_int(ws.cell(row=row_idx, column=col_map.get('nb_cases', 2)).value)
        nb_ok = safe_int(ws.cell(row=row_idx, column=col_map.get('nb_ok', 3)).value)
        nb_nok = safe_int(ws.cell(row=row_idx, column=col_map.get('nb_nok', 4)).value)
        
        # Calcul du taux si absent
        taux_val = ws.cell(row=row_idx, column=col_map.get('taux_ok', 5)).value
        if taux_val is not None and str(taux_val).strip():
            taux_ok = safe_float_pct(taux_val)
        else:
            taux_ok = round((nb_ok / nb_cases * 100), 1) if nb_cases > 0 else 0.0

        entries.append({
            'raw_team_name': raw_team,
            'team_id': team_id,
            'is_internal_team': is_internal,
            'nb_cases': nb_cases,
            'nb_ok': nb_ok,
            'nb_nok': nb_nok,
            'taux_ok': taux_ok
        })
        
    return entries


def parse_recap_image(file_path):
    """
    Parse une image de Récapitulatif (ex: image recap.jpeg) via OCR Tesseract / Regex.
    Extrait les lignes contenant : Equipe, Nombre de cas, OK, NOK, Taux %
    """
    import cv2
    import numpy as np
    import pytesseract
    from PIL import Image
    
    tesseract_cmd = os.environ.get('TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe')
    if os.path.exists(tesseract_cmd):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    # Prétraitement de l'image avec OpenCV pour un OCR net
    try:
        cv_img = cv2.imread(file_path)
        if cv_img is not None:
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            # Agrandir l'image si nécessaire
            if gray.shape[1] < 1500:
                scale = 1500.0 / gray.shape[1]
                gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            # Binarisation douce
            _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            processed_img = Image.fromarray(thresh)
        else:
            processed_img = Image.open(file_path)
    except Exception:
        processed_img = Image.open(file_path)

    custom_config = r'--oem 3 --psm 6'
    
    try:
        raw_text = pytesseract.image_to_string(processed_img, lang='fra+eng', config=custom_config)
    except Exception as e:
        print(f"[OCR Recap Error] {e}")
        return []

    team_data_cache = get_internal_team_keywords()
    entries = []
    
    lines = raw_text.split('\n')
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
            
        # On cherche les motifs : NOM_EQUIPE  NOMBRE_CAS  OK  [NOK]  [TAUX%]
        # Ex: BAMBA MBENGUE 119 79 40 66,4% ou BAMBA MBENGUE 119 79
        match = re.search(r'^([A-Z\s\.\-_]{3,35})\s+(\d{1,4})\s+(\d{1,4})(?:\s+(\d{1,4}))?(?:\s+([\d,\.]+\s*%?))?', line_str, re.IGNORECASE)
        if match:
            team_name = match.group(1).strip()
            norm_t = normalize_text(team_name)
            
            # Ignorer les en-têtes
            if any(k in norm_t for k in ['DASHBOARD', 'EQUIPE', 'NOMBRE', 'CAS', 'TAUX', 'INSTALLATION']):
                continue
                
            nb_cases = int(match.group(2))
            nb_ok = int(match.group(3))
            nb_nok = int(match.group(4)) if match.group(4) else max(0, nb_cases - nb_ok)
            
            if match.group(5):
                taux_str = match.group(5).replace('%', '').replace(',', '.').strip()
                try:
                    taux_ok = float(taux_str)
                except ValueError:
                    taux_ok = round((nb_ok / nb_cases * 100), 1) if nb_cases > 0 else 0.0
            else:
                taux_ok = round((nb_ok / nb_cases * 100), 1) if nb_cases > 0 else 0.0
                
            team_id, is_internal = match_team_name(team_name, team_data_cache)
            
            entries.append({
                'raw_team_name': team_name,
                'team_id': team_id,
                'is_internal_team': is_internal,
                'nb_cases': nb_cases,
                'nb_ok': nb_ok,
                'nb_nok': nb_nok,
                'taux_ok': taux_ok
            })
            
    return entries
